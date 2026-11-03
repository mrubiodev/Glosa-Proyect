# glosa-ingest

Extractores y chunkers de documentos.

## Qué hace

Convierte archivos en texto y el texto en fragmentos (chunks).

## Por qué existe como pieza separada

Cada tipo de documento se trocea de forma distinta; aislarlo permite añadir formatos sin tocar el resto.

## Cómo se usa

Implementa los puertos `TextExtractor` y `Chunker` de `glosa-core`. Ejemplo previsto: un extractor de Markdown y un chunker por encabezados.

## Qué se puede cambiar

Añadir extractores (PDF, DOCX, OCR) o chunkers (por tokens, semántico) como nuevos adaptadores.

## Estado

Esqueleto: pendiente de implementar. Ver `docs/SPEC.md`.
