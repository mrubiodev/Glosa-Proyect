"""Los adaptadores reales dentro del flujo completo de Glosa (subir → worker → buscar)."""
from glosa_core.domain import DocumentStatus, JobStatus
from glosa_core.testing_world import World
from glosa_ingest import HeadingChunker, MarkdownExtractor, PlainTextExtractor

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


def real_world(max_chars=1200) -> World:
    return World(
        extractors=[MarkdownExtractor(), PlainTextExtractor()],
        chunker=HeadingChunker(max_chars=max_chars),
    )


def test_un_markdown_se_indexa_por_secciones_y_se_encuentra_por_su_contenido():
    w = real_world()
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, CONTRATO, title="Contrato", source_type="markdown")
    w.run_jobs()

    assert w.documents.get(col.id, res.document_id).status is DocumentStatus.READY
    chunks = w.index.all_chunks(col.id)
    assert [c.metadata["heading_path"] for c in chunks] == [
        "Contrato", "Contrato > Pagos", "Contrato > Rescisión",
    ]
    assert all("title: Contrato de servicios" not in c.text for c in chunks)  # sin front matter

    hits = w.search.execute(w.ctx(ana), col.id, "preaviso")
    assert len(hits) == 1
    assert hits[0].chunk.metadata["heading_path"] == "Contrato > Rescisión"
    assert hits[0].chunk.metadata["title"] == "Contrato"


def test_se_puede_buscar_por_el_titulo_de_la_seccion():
    w = real_world()
    ana = w.user("ana")
    col = w.new_collection("ana")
    w.upload(ana, col.id, CONTRATO, source_type="markdown")
    w.run_jobs()
    hits = w.search.execute(w.ctx(ana), col.id, "Pagos")
    assert [h.chunk.metadata["heading_path"] for h in hits] == ["Contrato > Pagos"]


def test_modificar_un_markdown_deja_solo_la_version_nueva():
    w = real_world()
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, CONTRATO, source_type="markdown")
    w.run_jobs()
    nuevo = CONTRATO.replace("quince días", "sesenta días")
    w.upload(ana, col.id, nuevo, source_type="markdown", document_id=res.document_id)
    w.run_jobs()
    assert w.search.execute(w.ctx(ana), col.id, "quince") == []
    assert len(w.search.execute(w.ctx(ana), col.id, "sesenta")) == 1


def test_un_archivo_que_no_es_utf8_acaba_en_dead_sin_reintentos():
    w = real_world()
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.submit.execute(
        w.ctx(ana), col.id, title="Latin1", source_type="text", content="canción".encode("latin-1")
    )
    w.run_jobs()
    job = w.queue.get(col.id, res.job.id)
    assert job.status is JobStatus.DEAD and job.attempts == 1
    assert "UTF-8" in job.error
    assert w.documents.get(col.id, res.document_id).status is DocumentStatus.FAILED


def test_un_markdown_que_solo_tiene_metadatos_no_tiene_texto_indexable():
    w = real_world()
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, "---\ntitle: vacío\n---\n", source_type="markdown")
    w.run_jobs()
    assert w.queue.get(col.id, res.job.id).status is JobStatus.DEAD
