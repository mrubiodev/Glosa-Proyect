"""Casos de uso (SPEC §11).

Cada uno autoriza con el servicio de autorización, actúa y deja constancia en el
registro de operaciones. Las escrituras no se ejecutan aquí: se encolan y las procesan
los manejadores (`handlers.py`) a través de `ProcessNextJob`.

Implementados: CreateCollection, IssueToken, RevokeToken, SubmitDocument,
SearchCollection, ReadDocument, ListDocuments, HandleIngest (ingest y modify) y
ProcessNextJob. El resto está en docs/PENDIENTE.md.
"""
from .access_tokens import IssuedToken, IssueToken, RevokeToken
from .collection import CreateCollection
from .documents import DocumentView, ListDocuments, ReadDocument, SubmitDocument, SubmitResult
from .handlers import HandleIngest
from .jobs import ProcessNextJob
from .search import SearchCollection

__all__ = [
    "CreateCollection",
    "DocumentView",
    "HandleIngest",
    "IssueToken",
    "IssuedToken",
    "ListDocuments",
    "ProcessNextJob",
    "ReadDocument",
    "RevokeToken",
    "SearchCollection",
    "SubmitDocument",
    "SubmitResult",
]
