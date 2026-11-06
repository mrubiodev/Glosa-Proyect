from datetime import datetime, timezone

import pytest

from glosa_core.domain import Document, DocumentStatus, DocumentVersion
from glosa_storage import SqliteDocumentRepository

NOW = datetime(2026, 3, 1, 9, 0, 0, 250000, tzinfo=timezone.utc)


def doc(doc_id="d1", collection="col-a", **kw):
    data = dict(id=doc_id, collection_id=collection, title="Contrato", source_type="markdown",
                current_version=0, status=DocumentStatus.PENDING, metadata={"cliente": "Acme", "n": 2})
    data.update(kw)
    return Document(**data)


def version(doc_id="d1", n=1, content=b"x"):
    return DocumentVersion(doc_id, n, f"hash{n}", len(content), "ana", NOW)


@pytest.fixture
def repo(db):
    return SqliteDocumentRepository(db)


def test_el_documento_y_su_version_sobreviven_al_guardado(repo):
    v = version(content=b"contenido")
    repo.add(doc(), v, b"contenido")
    assert repo.get("col-a", "d1") == doc()
    assert repo.history("col-a", "d1") == [v]


def test_el_contenido_binario_se_conserva_tal_cual(repo):
    raw = bytes(range(256)) + "canción ñ".encode() + b"\x00\x00fin"
    repo.add(doc(), version(content=raw), raw)
    repo.update_status("col-a", "d1", DocumentStatus.READY, current_version=1)
    assert repo.get_content("col-a", "d1", 1) == raw
    assert repo.get_content("col-a", "d1", None) == raw  # None = la vigente


def test_sin_version_vigente_no_hay_contenido_por_defecto(repo):
    repo.add(doc(), version(), b"x")
    assert repo.get_content("col-a", "d1", None) is None  # current_version = 0
    assert repo.get_content("col-a", "d1", 1) == b"x"


def test_historial_ordenado_y_versiones_inmutables(repo):
    repo.add(doc(), version(n=1), b"uno")
    repo.add_version("col-a", "d1", version(n=2), b"dos")
    repo.add_version("col-a", "d1", version(n=3), b"tres")
    assert [v.version for v in repo.history("col-a", "d1")] == [1, 2, 3]
    assert repo.get_content("col-a", "d1", 2) == b"dos"
    with pytest.raises(Exception):  # la clave primaria impide reescribir una versión
        repo.add_version("col-a", "d1", version(n=2), b"otra")
    assert repo.get_content("col-a", "d1", 2) == b"dos"


def test_anadir_version_a_un_documento_inexistente_falla(repo):
    with pytest.raises(KeyError):
        repo.add_version("col-a", "fantasma", version("fantasma"), b"x")


def test_cambiar_estado_conserva_o_actualiza_la_version_vigente(repo):
    repo.add(doc(), version(), b"x")
    repo.update_status("col-a", "d1", DocumentStatus.READY, current_version=1)
    repo.update_status("col-a", "d1", DocumentStatus.PROCESSING)  # sin versión: no la toca
    after = repo.get("col-a", "d1")
    assert after.status is DocumentStatus.PROCESSING and after.current_version == 1


def test_listar_excluye_los_borrados_y_respeta_el_orden(repo):
    for i in range(3):
        repo.add(doc(f"d{i}"), version(f"d{i}"), b"x")
    repo.mark_deleted("col-a", "d1", NOW)
    assert [d.id for d in repo.list("col-a")] == ["d0", "d2"]
    assert repo.get("col-a", "d1").deleted_at == NOW  # el borrado es lógico


def test_los_documentos_de_una_coleccion_no_se_ven_desde_otra(repo):
    repo.add(doc("d1", "col-a"), version("d1"), b"secreto de A")
    assert repo.get("col-b", "d1") is None
    assert repo.list("col-b") == []
    assert repo.get_content("col-b", "d1", 1) is None
    assert repo.history("col-b", "d1") == []


def test_el_mismo_id_en_dos_colecciones_son_documentos_distintos(repo):
    repo.add(doc("d1", "col-a", title="A"), version("d1"), b"a")
    repo.add(doc("d1", "col-b", title="B"), version("d1"), b"b")
    assert repo.get("col-a", "d1").title == "A" and repo.get("col-b", "d1").title == "B"
    assert repo.get_content("col-a", "d1", 1) == b"a" and repo.get_content("col-b", "d1", 1) == b"b"


def test_no_se_puede_repetir_el_id_en_la_misma_coleccion(repo):
    repo.add(doc(), version(), b"x")
    with pytest.raises(Exception):
        repo.add(doc(), version(), b"x")
