"""Decodificación común a los extractores."""
from __future__ import annotations

from glosa_core.errors import PermanentJobError


def decode_text(raw: bytes) -> str:
    """UTF-8 (con o sin BOM), con saltos de línea normalizados a `\\n`.

    Un archivo que no sea UTF-8 falla de forma permanente y con un mensaje claro:
    reintentarlo no lo arreglaría, y adivinar la codificación daría texto corrupto.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PermanentJobError("El archivo no está codificado en UTF-8") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
