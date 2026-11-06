"""La cola SQLite cumple el mismo contrato que la cola en memoria, y además es
segura entre procesos y no se deja duplicar por la base de datos."""
import sqlite3
import threading
from datetime import datetime, timezone

import pytest

from glosa_core.domain import Actor, ActorKind, Job, JobResult, JobStatus, JobType
from glosa_core.queue_contract import ALL_CHECKS
from glosa_core.testing import FixedClock
from glosa_storage import Database, SqliteJobQueue


@pytest.mark.parametrize("check", ALL_CHECKS, ids=lambda c: c.__name__)
def test_contrato_de_la_cola(check):
    check(lambda clock: SqliteJobQueue(Database(":memory:"), clock))


def make_job(job_id, doc="d1", key=None, collection="col-a", version=1) -> Job:
    return Job(
        id=job_id, collection_id=collection, type=JobType.MODIFY, target=doc, version=version,
        status=JobStatus.QUEUED,
        actor=Actor(ActorKind.TOKEN, "tok-1", "col-a", frozenset()),
        correlation_id="corr-xyz",
        created_at=datetime(2026, 1, 1, 12, 30, 15, 123456, tzinfo=timezone.utc),
        idempotency_key=key, priority=7, max_attempts=3,
    )


def test_todos_los_campos_sobreviven_al_guardado():
    q = SqliteJobQueue(Database(":memory:"), FixedClock())
    original = make_job("j1", key="k1")
    q.enqueue(original)
    assert q.get("col-a", "j1") == original


def test_un_trabajo_no_se_ve_desde_otra_coleccion():
    q = SqliteJobQueue(Database(":memory:"), FixedClock())
    q.enqueue(make_job("j1"))
    assert q.get("col-b", "j1") is None
    assert q.list("col-b", None, 10) == []
    assert q.cancel("col-b", "j1") is False


def test_el_indice_unico_impide_duplicar_la_clave_de_idempotencia_aunque_se_salte_la_cola():
    db = Database(":memory:")
    q = SqliteJobQueue(db, FixedClock())
    q.enqueue(make_job("j1", key="k"))
    with pytest.raises(sqlite3.IntegrityError):
        db.conn().execute(
            "INSERT INTO jobs (id, collection_id, type, target, status, actor_json, correlation_id, "
            "created_at, priority, attempts, max_attempts, idempotency_key) "
            "VALUES ('j2','col-a','ingest','d9','queued','{}','c','t',1,0,3,'k')"
        )


def test_confirmar_o_fallar_un_trabajo_que_no_esta_en_marcha_no_hace_nada():
    q = SqliteJobQueue(Database(":memory:"), FixedClock())
    q.enqueue(make_job("j1"))
    q.ack("j1", JobResult())  # sigue en cola: no puede darse por hecho
    assert q.get("col-a", "j1").status is JobStatus.QUEUED
    q.fail("j1", "x", None)
    assert q.get("col-a", "j1").status is JobStatus.QUEUED


def test_heartbeat_renueva_el_lease():
    clock = FixedClock()
    q = SqliteJobQueue(Database(":memory:"), clock)
    q.enqueue(make_job("j1"))
    q.claim("w1", 30)
    clock.advance(seconds=20)
    q.heartbeat("j1", "w1")  # lease hasta t+50
    clock.advance(seconds=25)  # t+45: sin heartbeat ya habría caducado
    assert q.claim("w2", 30) is None
    clock.advance(seconds=10)  # t+55: ahora sí
    assert q.claim("w2", 30).id == "j1"


def test_varios_workers_a_la_vez_nunca_reciben_el_mismo_trabajo(tmp_path):
    """Hilos con conexiones propias sobre el mismo archivo, como harían varios procesos."""
    db = Database(tmp_path / "q.db")
    clock = FixedClock()
    q = SqliteJobQueue(db, clock)
    total = 40
    for i in range(total):
        q.enqueue(make_job(f"j{i}", doc=f"d{i}"))  # documentos distintos: ninguno bloquea a otro

    claimed: list[str] = []
    lock = threading.Lock()
    errors: list[BaseException] = []

    def worker(name):
        try:
            while True:
                job = q.claim(name, 60)
                if job is None:
                    return
                with lock:
                    claimed.append(job.id)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(f"w{n}",)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(claimed) == total
    assert len(set(claimed)) == total  # ninguno duplicado
    db.close()


def test_encolar_la_misma_clave_desde_varios_hilos_crea_un_solo_trabajo(tmp_path):
    db = Database(tmp_path / "q.db")
    q = SqliteJobQueue(db, FixedClock())
    results: list[str] = []

    def submit(n):
        results.append(q.enqueue(make_job(f"j{n}", key="misma")).id)

    threads = [threading.Thread(target=submit, args=(n,)) for n in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(results)) == 1
    assert len(q.list("col-a", None, 100)) == 1
    db.close()
