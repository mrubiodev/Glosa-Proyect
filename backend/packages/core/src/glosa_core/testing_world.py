"""Un mundo completo en memoria para probar los casos de uso de extremo a extremo.

Es reutilizable: otros paquetes (ingest, storage...) lo usan para probar sus piezas
dentro del flujo real, sustituyendo extractores, chunker o repositorios.
"""
from __future__ import annotations

import importlib
import os

from .authorization import AuthorizationService
from .context import RequestContext
from .domain import (
    Actor,
    ActorKind,
    Channel,
    Collection,
    CollectionSettings,
    Credentials,
    JobType,
    Scope,
)
from .kernel import Kernel
from .recorder import OperationRecorder
from .testing import (
    FakeChunker,
    FakeExtractor,
    FixedClock,
    InMemoryAccessRepository,
    InMemoryChunkIndex,
    InMemoryCollectionRepository,
    InMemoryDocumentRepository,
    InMemoryJobQueue,
    InMemoryOperationLog,
    SequentialIds,
)
from .tokens import TokenAuthenticator
from .uow import NoTransaction
from .usecases import (
    CancelJob,
    CreateCollection,
    GetJob,
    HandleIngest,
    IssueToken,
    ListDocuments,
    ListJobs,
    ProcessNextJob,
    QueryOperations,
    ReadDocument,
    RevokeToken,
    SearchCollection,
    SubmitDocument,
    VerifyOperationLog,
    ViewTrace,
)


def adapters_from_env(clock) -> dict:
    """Permite ejecutar toda la batería de tests contra adaptadores reales.

    `GLOSA_TEST_ADAPTERS=paquete.modulo:funcion` apunta a una función que recibe el reloj y
    devuelve un diccionario con los adaptadores (access, collections, documents, index,
    queue, log, uow). `core` no conoce ningún adaptador concreto: solo importa lo que se
    le indique.
    """
    spec = os.environ.get("GLOSA_TEST_ADAPTERS")
    if not spec:
        return {}
    module_name, _, function = spec.partition(":")
    return getattr(importlib.import_module(module_name), function)(clock)


class World:
    def __init__(
        self,
        settings: CollectionSettings | None = None,
        extractors=None,
        chunker=None,
        adapters: dict | None = None,
        clock: FixedClock | None = None,
        ids=None,
    ) -> None:
        self.clock = clock or FixedClock()
        self.ids = ids or SequentialIds()
        given = adapters if adapters is not None else adapters_from_env(self.clock)

        def pick(name, default):
            return given[name] if name in given else default()

        self.access = pick("access", InMemoryAccessRepository)
        self.collections = pick("collections", InMemoryCollectionRepository)
        self.documents = pick("documents", InMemoryDocumentRepository)
        self.index = pick("index", InMemoryChunkIndex)
        self.queue = pick("queue", lambda: InMemoryJobQueue(self.clock))
        self.log = pick("log", InMemoryOperationLog)
        self.uow = pick("uow", NoTransaction)

        self.kernel = Kernel(
            authz=AuthorizationService(self.access),
            recorder=OperationRecorder(self.log, self.clock, self.ids),
            clock=self.clock,
            ids=self.ids,
            uow=self.uow,
        )
        extractors = extractors if extractors is not None else [FakeExtractor()]
        chunker = chunker if chunker is not None else FakeChunker()
        self.create_collection = CreateCollection(
            self.kernel, self.collections, self.access, settings
        )
        self.issue_token = IssueToken(self.kernel, self.access)
        self.revoke_token = RevokeToken(self.kernel, self.access)
        self.submit = SubmitDocument(
            self.kernel, self.collections, self.documents, self.queue, extractors
        )
        self.search = SearchCollection(self.kernel, self.collections, self.index)
        self.read = ReadDocument(self.kernel, self.documents)
        self.list_docs = ListDocuments(self.kernel, self.documents)
        self.handler = HandleIngest(
            self.kernel, self.documents, self.index, extractors, chunker
        )
        self.process = ProcessNextJob(
            self.kernel,
            self.queue,
            {JobType.INGEST: self.handler, JobType.MODIFY: self.handler},
        )
        self.authenticator = TokenAuthenticator(self.access, self.clock)
        self.get_job = GetJob(self.kernel, self.queue)
        self.list_jobs = ListJobs(self.kernel, self.queue)
        self.cancel_job = CancelJob(self.kernel, self.queue, self.documents)
        self.query_ops = QueryOperations(self.kernel, self.log)
        self.verify_ops = VerifyOperationLog(self.kernel, self.log)
        self.view_trace = ViewTrace(self.kernel, self.log)

    # --- ayudas ---------------------------------------------------------

    @staticmethod
    def user(user_id: str) -> Actor:
        return Actor(ActorKind.USER, user_id)

    def ctx(self, actor: Actor, channel: Channel = Channel.API) -> RequestContext:
        return RequestContext.new(actor, channel, self.ids)

    def new_collection(self, owner: str, name: str = "Docs") -> Collection:
        return self.create_collection.execute(self.ctx(self.user(owner)), name)

    def token_actor(self, owner: str, collection_id: str, *scopes: Scope) -> Actor:
        """Emite un token con el propietario y devuelve el actor ya autenticado con él."""
        issued = self.issue_token.execute(
            self.ctx(self.user(owner)), collection_id, scopes or (Scope.READ,)
        )
        actor = self.authenticator.identify(Credentials(issued.raw))
        assert actor is not None
        return actor

    def upload(
        self,
        actor: Actor,
        collection_id: str,
        text: str,
        title: str = "Doc",
        source_type: str = "text",
        **kw,
    ):
        return self.submit.execute(
            self.ctx(actor),
            collection_id,
            title=title,
            source_type=source_type,
            content=text.encode("utf-8"),
            **kw,
        )

    def tamper_log(self, collection_id: str, index: int, **changes) -> str:
        """Altera una entrada del registro (para probar la detección). Devuelve su id."""
        return self.log.tamper(collection_id, index, **changes)

    def force_source_type(self, collection_id: str, doc_id: str, source_type: str) -> None:
        self.documents.force_source_type(collection_id, doc_id, source_type)

    def run_jobs(self) -> int:
        done = 0
        while self.process.execute() is not None:
            done += 1
        return done
