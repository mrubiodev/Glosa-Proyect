"""Un mundo completo en memoria para probar los casos de uso de extremo a extremo.

Es reutilizable: otros paquetes (ingest, storage...) lo usan para probar sus piezas
dentro del flujo real, sustituyendo extractores, chunker o repositorios.
"""
from __future__ import annotations

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
)


class World:
    def __init__(
        self,
        settings: CollectionSettings | None = None,
        extractors=None,
        chunker=None,
    ) -> None:
        self.clock = FixedClock()
        self.ids = SequentialIds()
        self.access = InMemoryAccessRepository()
        self.collections = InMemoryCollectionRepository()
        self.documents = InMemoryDocumentRepository()
        self.index = InMemoryChunkIndex()
        self.queue = InMemoryJobQueue(self.clock)
        self.log = InMemoryOperationLog()

        self.kernel = Kernel(
            authz=AuthorizationService(self.access),
            recorder=OperationRecorder(self.log, self.clock, self.ids),
            clock=self.clock,
            ids=self.ids,
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

    def run_jobs(self) -> int:
        done = 0
        while self.process.execute() is not None:
            done += 1
        return done
