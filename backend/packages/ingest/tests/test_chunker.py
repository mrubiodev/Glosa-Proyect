import pytest

from glosa_ingest import HeadingChunker


def texts(drafts):
    return [d.text for d in drafts]


def test_texto_vacio_o_en_blanco_no_da_fragmentos():
    chunker = HeadingChunker()
    assert chunker.split("") == []
    assert chunker.split("  \n\n \n") == []


def test_sin_encabezados_trocea_por_parrafos_y_los_agrupa():
    drafts = HeadingChunker(max_chars=40).split("Uno.\n\nDos.\n\nTres cosas largas que no caben juntas.")
    assert texts(drafts) == ["Uno.\n\nDos.", "Tres cosas largas que no caben juntas."]
    assert all(d.metadata == {"heading_path": "", "level": 0} for d in drafts)


def test_cada_seccion_lleva_su_ruta_de_encabezados():
    doc = "Preámbulo.\n\n# Contrato\n\nTexto A.\n\n## Pagos\n\nTexto B.\n\n## Plazos\n\nTexto C.\n\n# Anexo\n\nTexto D."
    drafts = HeadingChunker().split(doc)
    assert [d.metadata["heading_path"] for d in drafts] == [
        "", "Contrato", "Contrato > Pagos", "Contrato > Plazos", "Anexo",
    ]
    assert [d.metadata["level"] for d in drafts] == [0, 1, 2, 2, 1]


def test_el_fragmento_incluye_su_encabezado_para_que_se_pueda_buscar_por_el():
    drafts = HeadingChunker().split("# Contrato\n\n## Rescisión\n\nPreaviso de 30 días.")
    assert drafts[0].text == "## Rescisión\n\nPreaviso de 30 días."


def test_se_puede_no_incluir_el_encabezado():
    drafts = HeadingChunker(include_heading=False).split("# Contrato\n\nTexto.")
    assert drafts[0].text == "Texto."
    assert drafts[0].metadata["heading_path"] == "Contrato"


def test_un_encabezado_sin_contenido_no_genera_fragmento_pero_si_ruta_para_los_hijos():
    drafts = HeadingChunker().split("# A\n\n## B\n\nTexto.")
    assert len(drafts) == 1
    assert drafts[0].metadata["heading_path"] == "A > B"


def test_el_nivel_se_reinicia_al_volver_a_un_encabezado_superior():
    doc = "# A\n\n## B\n\n### C\n\nc.\n\n## D\n\nd."
    paths = [d.metadata["heading_path"] for d in HeadingChunker().split(doc)]
    assert paths == ["A > B > C", "A > D"]


@pytest.mark.parametrize(
    "line",
    ["#hashtag sin espacio", "####### siete almohadillas", "    # sangrado de código"],
)
def test_lo_que_no_es_un_encabezado_no_lo_es(line):
    drafts = HeadingChunker().split(f"{line}\n\ntexto")
    assert all(d.metadata["level"] == 0 for d in drafts)


def test_las_almohadillas_de_cierre_se_ignoran():
    drafts = HeadingChunker().split("## Título ##\n\nTexto.")
    assert drafts[0].metadata["heading_path"] == "Título"


def test_los_encabezados_dentro_de_un_bloque_de_codigo_no_cuentan():
    doc = "# Real\n\n```python\n# comentario, no encabezado\nx = 1\n```\n\nFin."
    drafts = HeadingChunker().split(doc)
    assert [d.metadata["heading_path"] for d in drafts] == ["Real"]
    assert "# comentario, no encabezado" in drafts[0].text


def test_un_bloque_de_codigo_con_lineas_en_blanco_no_se_parte():
    doc = "```\nlinea 1\n\nlinea 2\n```"
    drafts = HeadingChunker().split(doc)
    assert texts(drafts) == [doc]


def test_un_bloque_de_codigo_sin_cerrar_llega_hasta_el_final():
    drafts = HeadingChunker().split("Antes.\n\n```\ncodigo\n# no es titulo")
    assert "# no es titulo" in drafts[-1].text
    assert all(d.metadata["level"] == 0 for d in drafts)


def test_el_codigo_con_tildes_tambien_cuenta_como_bloque():
    drafts = HeadingChunker().split("~~~\n# dentro\n~~~\n\n# Fuera\n\nTexto.")
    assert [d.metadata["heading_path"] for d in drafts] == ["", "Fuera"]


def test_un_parrafo_largo_se_parte_por_frases():
    frases = ". ".join(f"Frase numero {i} del documento" for i in range(12)) + "."
    drafts = HeadingChunker(max_chars=100).split(frases)
    assert len(drafts) > 1
    assert all(len(d.text) <= 100 for d in drafts)
    assert " ".join(texts(drafts)).replace("  ", " ") == frases  # no se pierde nada


def test_una_palabra_mas_larga_que_el_limite_se_corta():
    drafts = HeadingChunker(max_chars=30).split("x" * 100)
    assert all(len(d.text) <= 30 for d in drafts)
    assert "".join(texts(drafts)) == "x" * 100


def test_un_codigo_largo_se_parte_por_lineas():
    code = "```\n" + "\n".join(f"linea {i}" for i in range(40)) + "\n```"
    drafts = HeadingChunker(max_chars=80).split(code)
    assert len(drafts) > 1 and all(len(d.text) <= 80 for d in drafts)


def test_los_fragmentos_respetan_el_limite_incluyendo_el_encabezado():
    doc = "# Titulo\n\n" + "\n\n".join(f"Parrafo {i} con algo de texto." for i in range(30))
    drafts = HeadingChunker(max_chars=150).split(doc)
    assert len(drafts) > 3
    assert all(len(d.text) <= 150 for d in drafts)
    assert all(d.text.startswith("# Titulo") for d in drafts)


def test_las_posiciones_son_consecutivas_y_el_resultado_es_determinista():
    doc = "# A\n\n" + "\n\n".join(f"p{i} " * 20 for i in range(10)) + "\n\n# B\n\nfin"
    first = HeadingChunker(max_chars=120).split(doc)
    assert [d.position for d in first] == list(range(len(first)))
    assert HeadingChunker(max_chars=120).split(doc) == first


def test_max_chars_demasiado_pequeno_es_un_error():
    with pytest.raises(ValueError):
        HeadingChunker(max_chars=5)
