from dataclasses import replace
from datetime import datetime, timezone

from glosa_core.chain import GENESIS_HASH, seal, verify
from glosa_core.domain import Actor, ActorKind, Channel, OperationEntry, Outcome


def entry(n: int, **details) -> OperationEntry:
    return OperationEntry(
        id=f"op-{n}",
        at=datetime(2026, 1, 1, 0, 0, n, tzinfo=timezone.utc),
        correlation_id="corr-1",
        actor=Actor(ActorKind.USER, "ana"),
        channel=Channel.API,
        action="document.ingest",
        collection_id="col-a",
        outcome=Outcome.SUCCEEDED,
        details=details,
    )


def build(n: int) -> list[OperationEntry]:
    out: list[OperationEntry] = []
    prev = None
    for i in range(n):
        sealed = seal(entry(i, chunks=i), prev)
        out.append(sealed)
        prev = sealed.hash
    return out


def test_la_primera_entrada_parte_del_genesis():
    assert build(1)[0].prev_hash == GENESIS_HASH


def test_cadena_intacta_es_valida():
    report = verify(build(5))
    assert report.valid and report.checked == 5


def test_manipular_una_entrada_invalida_la_cadena():  # prueba obligatoria 13
    chain = build(5)
    chain[2] = replace(chain[2], outcome=Outcome.DENIED)
    report = verify(chain)
    assert not report.valid
    assert report.broken_at == "op-2"


def test_eliminar_una_entrada_intermedia_se_detecta():
    chain = build(5)
    del chain[2]
    report = verify(chain)
    assert not report.valid
    assert report.broken_at == "op-3"


def test_tras_una_purga_la_cadena_restante_sigue_siendo_valida():
    chain = build(5)[2:]  # se purgaron las dos primeras por retención
    assert verify(chain).valid
