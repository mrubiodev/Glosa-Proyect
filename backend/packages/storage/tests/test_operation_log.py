import threading
from datetime import datetime, timedelta, timezone

import pytest

from glosa_core.domain import (
    Actor, ActorKind, Channel, OperationEntry, OperationFilter, Outcome, Scope,
)
from glosa_storage import Database, SqliteOperationLog
from glosa_storage.testing import OperationLogWithHooks

T0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def entry(n, collection="col-a", action="document.submit", outcome=Outcome.SUCCEEDED,
          corr="corr-1", actor="ana", at=None, **details):
    return OperationEntry(
        id=f"op-{n}", at=at or T0 + timedelta(seconds=n, microseconds=n * 7), correlation_id=corr,
        actor=Actor(ActorKind.USER, actor), channel=Channel.API, action=action,
        collection_id=collection, outcome=outcome, target={"document_id": f"d{n}", "version": n},
        duration_ms=n, details=details,
    )


@pytest.fixture
def log(db):
    return OperationLogWithHooks(db)


def test_lo_guardado_se_lee_igual_salvo_el_sellado(log):
    original = entry(1, query="hola ñ", hits=[{"score": 1.5, "chunk_id": "c1"}], none=None, flag=True)
    log.record(original)
    stored = log.query("col-a", OperationFilter(), 10)[0]
    assert stored.hash and stored.prev_hash
    assert {**stored.__dict__, "hash": None, "prev_hash": None} == \
           {**original.__dict__, "hash": None, "prev_hash": None}


def test_el_actor_con_scopes_sobrevive_al_guardado(log):
    token = Actor(ActorKind.TOKEN, "tok-1", "col-a", frozenset({Scope.READ, Scope.WRITE}))
    e = entry(1)
    log.record(OperationEntry(**{**e.__dict__, "actor": token}))
    assert log.query("col-a", OperationFilter(), 1)[0].actor == token


def test_la_cadena_es_valida_y_encadena_cada_entrada_con_la_anterior(log):
    for n in range(1, 6):
        log.record(entry(n))
    entries = log.query("col-a", OperationFilter(), 10)
    assert log.verify_chain("col-a").valid
    assert entries[0].prev_hash == "0" * 64
    assert all(entries[i].prev_hash == entries[i - 1].hash for i in range(1, 5))


def test_cada_coleccion_tiene_su_propia_cadena(log):
    log.record(entry(1, collection="col-a"))
    log.record(entry(2, collection="col-b"))
    log.record(entry(3, collection="col-a"))
    a = log.query("col-a", OperationFilter(), 10)
    assert a[1].prev_hash == a[0].hash
    assert log.query("col-b", OperationFilter(), 10)[0].prev_hash == "0" * 64
    assert log.verify_chain("col-a").valid and log.verify_chain("col-b").valid


def test_las_entradas_sin_coleccion_tienen_su_cadena_aparte(log):
    log.record(entry(1, collection=None, action="collection.create"))
    log.record(entry(2, collection=None, action="collection.create"))
    assert len(log.query(None, OperationFilter(), 10)) == 2
    assert log.query("col-a", OperationFilter(), 10) == []
    assert log.verify_chain(None).valid


def test_manipular_una_entrada_directamente_en_la_base_se_detecta(log):
    for n in range(1, 6):
        log.record(entry(n))
    tampered = log.tamper("col-a", 2, outcome=Outcome.DENIED)
    report = log.verify_chain("col-a")
    assert not report.valid and report.broken_at == tampered


def test_borrar_una_entrada_intermedia_se_detecta(log):
    for n in range(1, 6):
        log.record(entry(n))
    log._db.conn().execute("DELETE FROM operations WHERE id = 'op-3'")
    report = log.verify_chain("col-a")
    assert not report.valid and report.broken_at == "op-4"


def test_la_cadena_sobrevive_a_cerrar_y_reabrir_la_base(tmp_path):
    path = tmp_path / "g.db"
    first = Database(path)
    SqliteOperationLog(first).record(entry(1))
    SqliteOperationLog(first).record(entry(2))
    first.close()
    second = SqliteOperationLog(Database(path))
    second.record(entry(3))  # continúa la cadena existente
    assert second.verify_chain("col-a").valid
    assert [e.id for e in second.query("col-a", OperationFilter(), 10)] == ["op-1", "op-2", "op-3"]


def test_varios_hilos_escribiendo_a_la_vez_no_rompen_la_cadena(tmp_path):
    db = Database(tmp_path / "g.db")
    log = SqliteOperationLog(db)
    counter = iter(range(10_000))
    lock = threading.Lock()

    def write():
        for _ in range(25):
            with lock:
                n = next(counter)
            log.record(entry(n))

    threads = [threading.Thread(target=write) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    report = log.verify_chain("col-a")
    assert report.valid and report.checked == 100
    db.close()


def test_filtros(log):
    log.record(entry(1, action="document.submit", actor="ana", corr="c1"))
    log.record(entry(2, action="search.execute", actor="edu", corr="c2"))
    log.record(entry(3, action="search.execute", actor="ana", corr="c3", outcome=Outcome.DENIED))

    def ids(**kw):
        return [e.id for e in log.query("col-a", OperationFilter(**kw), 10)]

    assert ids() == ["op-1", "op-2", "op-3"]
    assert ids(action="search.execute") == ["op-2", "op-3"]
    assert ids(actor_id="ana") == ["op-1", "op-3"]
    assert ids(correlation_id="c2") == ["op-2"]
    assert ids(outcome=Outcome.DENIED) == ["op-3"]
    assert ids(action="search.execute", actor_id="ana") == ["op-3"]
    assert ids(since=T0 + timedelta(seconds=2)) == ["op-2", "op-3"]
    assert ids(until=T0 + timedelta(seconds=2)) == ["op-1"]
    assert [e.id for e in log.query("col-a", OperationFilter(), 2)] == ["op-1", "op-2"]


def test_las_entradas_de_una_coleccion_no_aparecen_en_otra(log):
    log.record(entry(1, collection="col-a"))
    assert log.query("col-b", OperationFilter(), 10) == []


def test_una_fecha_con_otra_zona_horaria_se_normaliza_y_la_cadena_sigue_valida(log):
    madrid = timezone(timedelta(hours=2))
    log.record(entry(1, at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=madrid)))
    stored = log.query("col-a", OperationFilter(), 1)[0]
    assert stored.at == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert log.verify_chain("col-a").valid
