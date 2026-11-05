import pytest

from glosa_core.errors import PermanentJobError
from glosa_ingest import MarkdownExtractor, PlainTextExtractor, strip_front_matter


def test_cada_extractor_declara_su_tipo():
    assert PlainTextExtractor().supports("text") and not PlainTextExtractor().supports("markdown")
    assert MarkdownExtractor().supports("markdown") and not MarkdownExtractor().supports("text")
    assert not MarkdownExtractor().supports("pdf")


def test_texto_utf8_con_acentos_y_bom():
    raw = "\ufeffCláusula de rescisión ñ".encode("utf-8")
    assert PlainTextExtractor().extract(raw) == "Cláusula de rescisión ñ"


def test_los_saltos_de_linea_se_normalizan():
    assert PlainTextExtractor().extract(b"uno\r\ndos\rtres\ncuatro") == "uno\ndos\ntres\ncuatro"


def test_los_bytes_nulos_se_eliminan():
    assert PlainTextExtractor().extract(b"a\x00b") == "ab"


@pytest.mark.parametrize("extractor", [PlainTextExtractor(), MarkdownExtractor()])
def test_un_archivo_que_no_es_utf8_falla_de_forma_permanente(extractor):
    with pytest.raises(PermanentJobError, match="UTF-8"):
        extractor.extract("canción".encode("latin-1"))


def test_markdown_conserva_los_encabezados():
    raw = b"# Titulo\n\nTexto con **negrita**."
    assert MarkdownExtractor().extract(raw) == "# Titulo\n\nTexto con **negrita**."


def test_se_quita_el_front_matter_yaml():
    raw = b"---\ntitle: Contrato\nversion: 2\n---\n\n# Cuerpo\n\nTexto."
    assert MarkdownExtractor().extract(raw) == "# Cuerpo\n\nTexto."


def test_una_regla_horizontal_inicial_no_es_front_matter():
    text = "---\n\nIntro\n\n---\n\nResto"
    assert strip_front_matter(text) == text


def test_front_matter_sin_cierre_se_deja_intacto():
    text = "---\ntitle: algo\n\nTexto sin cierre"
    assert strip_front_matter(text) == text


def test_el_front_matter_solo_cuenta_al_principio():
    text = "Intro\n\n---\ntitle: x\n---\n\nResto"
    assert strip_front_matter(text) == text
