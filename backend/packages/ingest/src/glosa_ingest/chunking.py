"""Chunker por encabezados (implementa el puerto Chunker).

Divide un documento por sus encabezados Markdown (`#` a `######`), recuerda la ruta de
encabezados de cada sección ("Contrato > Pagos > Plazos") y empaqueta los párrafos de cada
sección en fragmentos de un tamaño aproximado. Sirve también para texto plano: sin
encabezados, trocea por párrafos.

Limitaciones conocidas (ver docs/PENDIENTE.md): solo encabezados ATX (`# Título`), no los
subrayados con `===` o `---`; las tablas y listas se tratan como párrafos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from glosa_core.domain import ChunkDraft

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


@dataclass
class _Section:
    path: str  # "A > B"; vacío antes del primer encabezado
    level: int  # 0 si no hay encabezado
    heading_line: str  # "## B"; vacío si no hay encabezado
    blocks: list[str] = field(default_factory=list)  # párrafos o bloques de código


class HeadingChunker:
    def __init__(self, max_chars: int = 1200, include_heading: bool = True) -> None:
        if max_chars < 20:
            raise ValueError("max_chars debe ser al menos 20")
        self._max = max_chars
        self._include_heading = include_heading

    def split(self, text: str) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for section in self._sections(text):
            prefix = section.heading_line if self._include_heading else ""
            # El presupuesto del cuerpo descuenta el encabezado, sin pasar de la mitad
            budget = self._max if not prefix else max(self._max - len(prefix) - 2, self._max // 2)
            for body in self._pack(section.blocks, budget):
                chunk_text = f"{prefix}\n\n{body}" if prefix else body
                drafts.append(
                    ChunkDraft(
                        text=chunk_text,
                        position=len(drafts),
                        metadata={"heading_path": section.path, "level": section.level},
                    )
                )
        return drafts

    # --- Paso 1: dividir en secciones y bloques ------------------------------

    def _sections(self, text: str) -> list[_Section]:
        sections = [_Section("", 0, "")]
        stack: list[tuple[int, str]] = []  # (nivel, título)
        paragraph: list[str] = []
        code: list[str] = []
        fence: tuple[str, int] | None = None  # (carácter, longitud) del bloque abierto

        def close_paragraph() -> None:
            if paragraph:
                block = "\n".join(paragraph).strip()
                if block:
                    sections[-1].blocks.append(block)
                paragraph.clear()

        def close_code() -> None:
            if code:
                sections[-1].blocks.append("\n".join(code))
                code.clear()

        for line in text.split("\n"):
            if fence is not None:  # dentro de un bloque de código: nada se interpreta
                code.append(line)
                stripped = line.strip()
                if stripped and set(stripped) == {fence[0]} and len(stripped) >= fence[1]:
                    close_code()
                    fence = None
                continue

            opener = _FENCE_OPEN.match(line)
            if opener:
                close_paragraph()
                marker = opener.group(1)
                fence = (marker[0], len(marker))
                code.append(line)
                continue

            heading = _HEADING.match(line)
            if heading:
                close_paragraph()
                level, title = len(heading.group(1)), heading.group(2).strip()
                stack = [h for h in stack if h[0] < level] + [(level, title)]
                sections.append(
                    _Section(" > ".join(t for _, t in stack), level, f"{'#' * level} {title}")
                )
            elif not line.strip():
                close_paragraph()
            else:
                paragraph.append(line)

        close_paragraph()
        close_code()  # un bloque de código sin cerrar llega hasta el final
        return sections

    # --- Paso 2: empaquetar bloques en fragmentos -------------------------------

    def _pack(self, blocks: list[str], budget: int) -> list[str]:
        pieces: list[str] = []
        for block in blocks:
            pieces.extend(self._split_long(block, budget) if len(block) > budget else [block])

        chunks: list[str] = []
        current = ""
        for piece in pieces:
            if current and len(current) + 2 + len(piece) > budget:
                chunks.append(current)
                current = piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
        if current:
            chunks.append(current)
        return chunks

    def _split_long(self, block: str, budget: int) -> list[str]:
        """Parte un bloque más grande que el presupuesto: por líneas si es código,
        por frases si es un párrafo, y por palabras o a corte duro como último recurso."""
        is_code = _FENCE_OPEN.match(block.split("\n", 1)[0]) is not None
        units = block.split("\n") if is_code else _SENTENCE_END.split(block)
        separator = "\n" if is_code else " "

        out: list[str] = []
        current = ""
        for unit in units:
            for part in self._fit(unit, budget):
                if current and len(current) + len(separator) + len(part) > budget:
                    out.append(current)
                    current = part
                else:
                    current = f"{current}{separator}{part}" if current else part
        if current:
            out.append(current)
        return out

    @staticmethod
    def _fit(unit: str, budget: int) -> list[str]:
        """Garantiza que ninguna unidad supere el presupuesto."""
        if len(unit) <= budget:
            return [unit]
        parts: list[str] = []
        current = ""
        for word in unit.split(" "):
            while len(word) > budget:  # palabra enorme: corte duro
                if current:
                    parts.append(current)
                    current = ""
                parts.append(word[:budget])
                word = word[budget:]
            if current and len(current) + 1 + len(word) > budget:
                parts.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            parts.append(current)
        return parts
