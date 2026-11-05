# glosa-ingest

Extractores y chunkers de documentos.

## Qué hace

Convierte archivos en texto y el texto en fragmentos (chunks), implementando los puertos `TextExtractor` y `Chunker` de `glosa-core`:

| Nombre | Puerto | Función |
|--------|--------|---------|
| `text` | `TextExtractor` | Texto plano UTF-8; normaliza saltos de línea |
| `markdown` | `TextExtractor` | Markdown; además retira el front matter YAML inicial |
| `headings` | `Chunker` | Trocea por encabezados, con la ruta de encabezados en los metadatos |

## Por qué existe como pieza separada

Cada tipo de documento se trocea de forma distinta; aislarlo permite añadir formatos sin tocar el resto del sistema.

## Cómo se usa suelto

```python
from glosa_ingest import HeadingChunker, MarkdownExtractor

text = MarkdownExtractor().extract(open("contrato.md", "rb").read())
for chunk in HeadingChunker(max_chars=1200).split(text):
    print(chunk.position, chunk.metadata["heading_path"], len(chunk.text))
```

Dentro de Glosa no hace falta importarlo: se registra solo por el entry point `glosa.adapters` y las plantillas lo piden por nombre (`extractors: [markdown, text]`, `chunker: headings`).

Reglas del chunker: los encabezados dentro de bloques de código no cuentan; un bloque de código no se parte por sus líneas en blanco; los párrafos se agrupan hasta `max_chars`, y uno demasiado largo se parte por frases, luego por palabras; el resultado es determinista.

## Qué se puede cambiar

Añadir extractores (PDF, DOCX, OCR) o chunkers (por tokens, semántico) como adaptadores nuevos y registrarlos con el mismo entry point.

## Estado

Implementado, con tests: extractores de texto y Markdown, chunker por encabezados y registro.
Limitaciones: solo encabezados ATX, solo UTF-8, tablas y listas como párrafos. Ver `docs/PENDIENTE.md`.
