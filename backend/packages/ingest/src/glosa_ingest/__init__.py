"""Extractores y chunkers de documentos."""
from .chunking import HeadingChunker
from .extractors import MarkdownExtractor, PlainTextExtractor, strip_front_matter

__all__ = [
    "HeadingChunker",
    "MarkdownExtractor",
    "PlainTextExtractor",
    "register",
    "strip_front_matter",
]


def register(registry) -> None:
    """Registra estos adaptadores por nombre en un registro de adaptadores.

    Se descubre solo, por el entry point `glosa.adapters`. El registro se recibe por
    parámetro (y solo se usa su método `register`) para no depender de otros paquetes.
    """
    registry.register("extractors", "markdown", MarkdownExtractor)
    registry.register("extractors", "text", PlainTextExtractor)
    registry.register("chunker", "headings", HeadingChunker)
