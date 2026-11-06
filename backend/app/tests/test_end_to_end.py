"""Glosa de punta a punta con los adaptadores REALES: ingest + SQLite en archivo.

Es el recorrido que hará el producto (subir → worker → buscar → auditar), sin HTTP todavía.
"""
from glosa_core.domain import Channel, OperationFilter, Scope
from glosa_core.system import UuidIds
from glosa_core.testing import FixedClock
from glosa_core.testing_world import World
from glosa_ingest import HeadingChunker, MarkdownExtractor, PlainTextExtractor
from glosa_storage.testing import make_adapters

CONTRATO = """---
title: Contrato de servicios
---

# Contrato

Este contrato regula la prestación del servicio.

## Pagos

El pago se realizará en un plazo de treinta días desde la factura.

## Rescisión

Cualquiera de las partes podrá rescindir con un preaviso de quince días.
"""


def real_world(path) -> World:
    clock = FixedClock()
    return World(
        extractors=[MarkdownExtractor(), PlainTextExtractor()],
        chunker=HeadingChunker(),
        adapters=make_adapters(clock, str(path)),
        clock=clock,
        ids=UuidIds(),
    )


def test_subir_un_markdown_buscarlo_y_auditarlo(tmp_path):
    w = real_world(tmp_path / "glosa.db")
    ana = w.user("ana")
    col = w.new_collection("ana", "Contratos")

    res = w.upload(ana, col.id, CONTRATO, title="Contrato", source_type="markdown")
    w.run_jobs()

    # búsqueda sin tildes ni mayúsculas, con procedencia
    hits = w.search.execute(w.ctx(ana), col.id, "RESCISION preaviso")
    assert len(hits) == 1
    chunk = hits[0].chunk
    assert chunk.metadata["heading_path"] == "Contrato > Rescisión"
    assert (chunk.document_id, chunk.version) == (res.document_id, 1)

    # un lector con token solo lee, y solo su colección
    reader = w.token_actor("ana", col.id, Scope.READ)
    assert len(w.search.execute(w.ctx(reader, Channel.MCP), col.id, "pagos")) == 1

    # el registro cuenta toda la historia de la subida con un solo correlation_id
    story = w.query_ops.execute(w.ctx(ana), col.id, OperationFilter(correlation_id=res.correlation_id))
    assert [e.action for e in story] == [
        "document.submit", "job.start", "document.extract", "document.chunk",
        "document.index", "document.ingest", "job.succeed",
    ]
    assert w.verify_ops.execute(w.ctx(ana), col.id).valid
    w.uow.close()


def test_modificar_y_consultar_la_version_vigente(tmp_path):
    w = real_world(tmp_path / "glosa.db")
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, CONTRATO, source_type="markdown")
    w.run_jobs()

    w.upload(ana, col.id, CONTRATO.replace("quince días", "sesenta días"),
             source_type="markdown", document_id=res.document_id)
    w.run_jobs()

    assert w.search.execute(w.ctx(ana), col.id, "quince") == []
    assert len(w.search.execute(w.ctx(ana), col.id, "sesenta")) == 1
    assert "quince" in w.read.execute(w.ctx(ana), col.id, res.document_id, version=1).text
    assert w.verify_ops.execute(w.ctx(ana), col.id).valid
    w.uow.close()
