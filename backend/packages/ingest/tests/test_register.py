from glosa_ingest import HeadingChunker, MarkdownExtractor, PlainTextExtractor, register


class FakeRegistry:
    def __init__(self):
        self.items = {}

    def register(self, kind, name, factory):
        self.items[(kind, name)] = factory


def test_registra_los_tres_adaptadores_con_los_nombres_de_las_plantillas():
    registry = FakeRegistry()
    register(registry)
    assert registry.items == {
        ("extractors", "markdown"): MarkdownExtractor,
        ("extractors", "text"): PlainTextExtractor,
        ("chunker", "headings"): HeadingChunker,
    }


def test_las_fabricas_construyen_instancias_utiles():
    registry = FakeRegistry()
    register(registry)
    assert registry.items[("chunker", "headings")]().split("hola")[0].text == "hola"
