"""Un mundo completo en memoria para probar los casos de uso de extremo a extremo."""
from __future__ import annotations

from glosa_core.authorization import AuthorizationService
from glosa_core.context import RequestContext
from glosa_core.domain import (
    Actor,
    ActorKind,
    Channel,
    Collection,
    CollectionSettings,
    Credentials,
    JobType,
    Scope,
)
from glosa_core.kernel import Kernel
from glosa_core.recorder import OperationRecorder
from glosa_core.testing import (
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
from glosa_core.tokens import TokenAuthenticator
from glosa_core.usecases import (
    CreateCollection,
    HandleIngest,
    IssueToken,
    ListDocuments,
    ProcessNextJob,
    ReadDocument,
    RevokeToken,
    SearchCollection,
    SubmitDocument,
)


class World:
    def __init__(self, settings: CollectionSettings | None = None) -> None:
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
        extractors = [FakeExtractor()]
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
            self.kernel, self.documents, self.index, extractors, FakeChunker()
        )
        self.process = ProcessNextJob(
            self.kernel,
            self.queue,
            {JobType.INGEST: self.handler, JobType.MODIFY: self.handler},
        )
        self.authenticator = TokenAuthenticator(self.access, self.clock)

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

    def upload(self, actor: Actor, collection_id: str, text: str, title: str = "Doc", **kw):
        return self.submit.execute(
            self.ctx(actor),
            collection_id,
            title=title,
            source_type="text",
            content=text.encode("utf-8"),
            **kw,
        )

    def run_jobs(self) -> int:
        done = 0
        while self.process.execute() is not None:
            done += 1
        return done
