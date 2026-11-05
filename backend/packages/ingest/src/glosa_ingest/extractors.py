"""Extractores de texto (implementan el puerto TextExtractor)."""
from __future__ import annotations

import re

from .decode import decode_text

_YAML_KEY = re.compile(r"^[\w.-]+\s*:")


class PlainTextExtractor:
    """Texto plano (`source_type = "text"`)."""

    def supports(self, source_type: str) -> bool:
        return source_type == "text"

    def extract(self, raw: bytes) -> str:
        return decode_text(raw)


class MarkdownExtractor:
    """Markdown (`source_type = "markdown"`).

    Conserva el Markdown tal cual, porque el chunker usa los encabezados para trocear
    y para citar. Solo retira el bloque de metadatos YAML (`front matter`) del
    principio, que no es contenido.
    """

    def supports(self, source_type: str) -> bool:
        return source_type == "markdown"

    def extract(self, raw: bytes) -> str:
        return strip_front_matter(decode_text(raw))


def strip_front_matter(text: str) -> str:
    """Quita un bloque `--- ... ---` inicial si parece YAML (al menos una línea `clave:`).

    Un documento que simplemente empieza con una regla horizontal `---` no se toca.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            block = lines[1:end]
            if any(_YAML_KEY.match(line) for line in block):
                return "\n".join(lines[end + 1 :]).lstrip("\n")
            return text
    return text  # sin cierre: no es front matter
