"""Casos de uso (SPEC §11).

Cada uno autoriza con el servicio de autorización, actúa y deja constancia en el
registro de operaciones. Las escrituras no se ejecutan aquí: se encolan y las procesan
los manejadores (`handlers.py`) a través de `ProcessNextJob`.

Implementados: CreateCollection, IssueToken, RevokeToken, SubmitDocument,
SearchCollection, ReadDocument, ListDocuments, GetJob, ListJobs, CancelJob,
QueryOperations, VerifyOperationLog, HandleIngest (ingest y modify) y
ProcessNextJob. El resto está en docs/PENDIENTE.md.
"""
from .access_tokens import IssuedToken, IssueToken, RevokeToken
from .collection import CreateCollection
from .documents import DocumentView, ListDocuments, ReadDocument, SubmitDocument, SubmitResult
from .handlers import HandleIngest
from .job_admin import CancelJob, GetJob, ListJobs
from .jobs import ProcessNextJob
from .operations import QueryOperations, VerifyOperationLog
from .search import SearchCollection

__all__ = [
    "CancelJob",
    "CreateCollection",
    "DocumentView",
    "GetJob",
    "HandleIngest",
    "IssueToken",
    "IssuedToken",
    "ListDocuments",
    "ListJobs",
    "ProcessNextJob",
    "QueryOperations",
    "ReadDocument",
    "RevokeToken",
    "SearchCollection",
    "SubmitDocument",
    "SubmitResult",
    "VerifyOperationLog",
]
