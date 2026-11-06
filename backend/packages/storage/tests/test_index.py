import pytest

from glosa_core.domain import Chunk
from glosa_storage import SqliteChunkIndex, fts_query


def chunk(cid, text, collection="col-a", doc="doc-1", version=1, position=0, **meta):
    return Chunk(cid, doc, version, collection, text, position, meta)


@pytest.fixture
def index(db):
    return SqliteChunkIndex(db)


def test_la_consulta_se_convierte_en_una_consulta_segura():
    assert fts_query('Rescisión anticipada') == '"rescisión" OR "anticipada"'
    assert fts_query("   ") == "" and fts_query("¿¡?!") == ""


@pytest.mark.parametrize("hostil", ['"', 'a" OR "b', "*", "NEAR(", "AND", "-x", "col:valor", "a OR", "'; DROP TABLE chunks;--"])
def test_una_consulta_con_sintaxis_de_fts_no_rompe_nada(index, hostil):
    index.index([chunk("c1", "texto normal con la palabra valor")])
    index.search("col-a", hostil, 5)  # no debe lanzar


def test_busca_sin_importar_mayusculas_ni_tildes(index):
    index.index([chunk("c1", "Cláusula de RESCISIÓN anticipada")])
    for query in ("rescision", "RESCISIÓN", "Rescisión", "clausula"):
        assert [h.chunk.id for h in index.search("col-a", query, 5)] == ["c1"]


def test_ordena_por_relevancia(index):
    index.index([
        chunk("poco", "El contrato menciona un plazo."),
        chunk("mucho", "El plazo de pago y el plazo de entrega: plazo, plazo, plazo."),
        chunk("nada", "Nada relacionado con el asunto."),
    ])
    hits = index.search("col-a", "plazo", 5)
    assert [h.chunk.id for h in hits] == ["mucho", "poco"]
    assert hits[0].score >= hits[1].score > 0


def test_una_consulta_de_varias_palabras_prefiere_los_que_tienen_mas(index):
    index.index([
        chunk("una", "solo menciona rescisión"),
        chunk("ambas", "la rescisión exige un preaviso de quince días"),
    ])
    assert index.search("col-a", "rescisión preaviso", 5)[0].chunk.id == "ambas"


def test_respeta_el_limite(index):
    index.index([chunk(f"c{i}", f"palabra comun numero{i}") for i in range(10)])
    assert len(index.search("col-a", "palabra", 3)) == 3


def test_el_aislamiento_por_coleccion_lo_hace_la_consulta(index):
    index.index([
        chunk("a1", "dato confidencial de A", collection="col-a"),
        chunk("b1", "dato confidencial de B", collection="col-b"),
    ])
    assert [h.chunk.id for h in index.search("col-a", "confidencial", 10)] == ["a1"]
    assert [h.chunk.id for h in index.search("col-b", "confidencial", 10)] == ["b1"]
    assert index.search("col-c", "confidencial", 10) == []


def test_el_mismo_id_en_dos_colecciones_son_fragmentos_distintos(index):
    index.index([chunk("x", "texto A", collection="col-a"), chunk("x", "texto B", collection="col-b")])
    assert index.search("col-a", "texto", 5)[0].chunk.text == "texto A"
    assert index.search("col-b", "texto", 5)[0].chunk.text == "texto B"


def test_devuelve_el_fragmento_completo_con_sus_metadatos(index):
    original = chunk("c1", "hola mundo", position=4, heading_path="A > B", level=2)
    index.index([original])
    assert index.search("col-a", "hola", 1)[0].chunk == original


def test_indexar_dos_veces_el_mismo_fragmento_no_lo_duplica(index):
    c = chunk("c1", "texto repetido")
    index.index([c])
    index.index([c])
    assert len(index.search("col-a", "repetido", 10)) == 1


def test_reindexar_un_id_con_texto_nuevo_reemplaza_al_anterior_tambien_en_la_busqueda(index):
    index.index([chunk("c1", "texto antiguo")])
    index.index([chunk("c1", "texto moderno")])
    assert index.search("col-a", "antiguo", 5) == []
    assert len(index.search("col-a", "moderno", 5)) == 1


def test_retirar_una_version_solo_quita_esa(index):
    index.index([
        chunk("v1", "version vieja", version=1),
        chunk("v2", "version nueva", version=2),
        chunk("otro", "version de otro documento", doc="doc-2", version=1),
    ])
    index.remove_version("col-a", "doc-1", 1)
    ids = {h.chunk.id for h in index.search("col-a", "version", 10)}
    assert ids == {"v2", "otro"}


def test_retirar_un_documento_quita_todas_sus_versiones(index):
    index.index([chunk("v1", "texto", version=1), chunk("v2", "texto", version=2),
                 chunk("otro", "texto", doc="doc-2")])
    index.remove_document("col-a", "doc-1")
    assert [h.chunk.id for h in index.search("col-a", "texto", 10)] == ["otro"]


def test_retirar_no_afecta_a_otra_coleccion(index):
    index.index([chunk("x", "texto", collection="col-a"), chunk("x", "texto", collection="col-b")])
    index.remove_document("col-a", "doc-1")
    assert index.search("col-a", "texto", 5) == []
    assert len(index.search("col-b", "texto", 5)) == 1
