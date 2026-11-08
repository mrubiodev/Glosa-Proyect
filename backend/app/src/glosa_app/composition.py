"""Composición: el único sitio donde la plantilla, los adaptadores y los casos de uso se unen.

Todo lo demás (core, storage, ingest, worker...) ignora a los demás. Aquí se lee qué pide la
plantilla activa, se buscan esos adaptadores por nombre en el registro y se construye el
sistema.
"""
from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from glosa_core.authorization import AuthorizationService
from glosa_core.context import RequestContext
from glosa_core.domain import Actor, ActorKind, Channel, CollectionSettings, Outcome
from glosa_core.kernel import Kernel
from glosa_core.recorder import OperationRecorder
from glosa_core.system import SystemClock, UuidIds
from glosa_core.tokens import TokenAuthenticator
from glosa_core.usecases import (
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
from glosa_core.domain import JobType
from glosa_templates import Registry, Template, load_template, validate_production

SYSTEM_ACTOR = Actor(ActorKind.SYSTEM, "system")
DEFAULT_TEMPLATE = "didactico"
DEFAULT_DATA_DIR = "./data"
DEFAULT_LEASE_SECONDS = 300


class ConfigurationError(Exception):
    """La plantilla pide algo que este despliegue no tiene."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("Configuración no válida:\n- " + "\n- ".join(problems))
        self.problems = problems


def register_builtins(registry: Registry) -> None:
    """Adaptadores que viven en `core` y por tanto no los registra ningún paquete externo."""
    registry.register("authenticator", "token", lambda storage, clock: TokenAuthenticator(storage.access, clock))
    registry.register("embedder", "none", lambda: None)


def default_registry() -> Registry:
    registry = Registry()
    register_builtins(registry)
    registry.load_entry_points()  # ingest, storage... lo que haya instalado
    return registry


def settings_from_template(template: Template) -> CollectionSettings:
    """Los ajustes con los que nace cada colección: los de la política de la plantilla."""
    get = template.get
    return CollectionSettings(
        query_logging=get("policy.query_logging"),
        retention_days=get("policy.retention_days"),
        version_retention=get("policy.version_retention"),
        version_keep=get("policy.version_keep"),
        hash_chain=get("policy.hash_chain"),
        max_file_mb=get("policy.limits.max_file_mb"),
        max_documents=get("policy.limits.max_documents"),
        max_queue_per_collection=get("policy.limits.max_queue_per_collection"),
    )


@dataclass
class Glosa:
    """El sistema ya construido: casos de uso listos para que los llamen la API, el MCP o el worker."""

    template: Template
    settings: CollectionSettings
    kernel: Kernel
    authenticator: Any
    storage: Any
    # casos de uso
    create_collection: CreateCollection
    issue_token: IssueToken
    revoke_token: RevokeToken
    submit: SubmitDocument
    search: SearchCollection
    read: ReadDocument
    list_documents: ListDocuments
    get_job: GetJob
    list_jobs: ListJobs
    cancel_job: CancelJob
    query_operations: QueryOperations
    verify_operations: VerifyOperationLog
    view_trace: ViewTrace
    process_next_job: ProcessNextJob

    def context(self, actor: Actor, channel: Channel = Channel.API) -> RequestContext:
        """Contexto nuevo para una petición, con su correlation_id."""
        return RequestContext.new(actor, channel, self.kernel.ids)

    def close(self) -> None:
        self.storage.close()


def build_app(
    template: Template,
    *,
    data_dir: str | Path,
    registry: Registry | None = None,
    clock=None,
    ids=None,
    worker_id: str = "worker-1",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> Glosa:
    """Construye el sistema que describe la plantilla.

    1. Aplica la guardia de producción: una plantilla insegura no arranca.
    2. Comprueba que todos los adaptadores que pide estén registrados.
    3. Los construye, cablea los casos de uso y deja constancia del arranque en el registro.
    """
    validate_production(template)
    registry = registry or default_registry()
    missing = registry.missing(template)
    if missing:
        raise ConfigurationError(missing)

    clock = clock or SystemClock()
    ids = ids or UuidIds()
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    get = template.get

    # --- adaptadores, por el nombre que pide la plantilla ----------------------------
    storage = registry.get("storage", get("adapters.storage"))(data_dir)
    queue = registry.get("queue", get("adapters.queue"))(storage, clock)
    index = registry.get("index", get("adapters.index"))(storage)
    extractors = [registry.get("extractors", n)() for n in get("adapters.extractors")]
    chunker = registry.get("chunker", get("adapters.chunker"))()
    authenticator = registry.get("authenticator", get("adapters.authenticator"))(storage, clock)

    kernel = Kernel(
        authz=AuthorizationService(storage.access),
        recorder=OperationRecorder(storage.log, clock, ids),
        clock=clock,
        ids=ids,
        uow=storage.uow,
    )
    settings = settings_from_template(template)
    ingest = HandleIngest(kernel, storage.documents, index, extractors, chunker)

    app = Glosa(
        template=template,
        settings=settings,
        kernel=kernel,
        authenticator=authenticator,
        storage=storage,
        create_collection=CreateCollection(kernel, storage.collections, storage.access, settings),
        issue_token=IssueToken(kernel, storage.access, get("policy.token_default_ttl_days")),
        revoke_token=RevokeToken(kernel, storage.access),
        submit=SubmitDocument(kernel, storage.collections, storage.documents, queue, extractors),
        search=SearchCollection(
            kernel, storage.collections, index,
            strategy=get("retrieval.strategy"), default_limit=get("retrieval.k"),
        ),
        read=ReadDocument(kernel, storage.documents),
        list_documents=ListDocuments(kernel, storage.documents),
        get_job=GetJob(kernel, queue),
        list_jobs=ListJobs(kernel, queue),
        cancel_job=CancelJob(kernel, queue, storage.documents),
        query_operations=QueryOperations(kernel, storage.log),
        verify_operations=VerifyOperationLog(kernel, storage.log),
        view_trace=ViewTrace(kernel, storage.log),
        process_next_job=ProcessNextJob(
            kernel, queue, {JobType.INGEST: ingest, JobType.MODIFY: ingest},
            worker_id=worker_id, lease_seconds=lease_seconds,
        ),
    )

    # Queda escrito con qué configuración arrancó este proceso
    kernel.recorder.record(
        RequestContext.new(SYSTEM_ACTOR, Channel.SYSTEM, ids),
        "template.applied",
        Outcome.SUCCEEDED,
        details={
            "name": template.name,
            "mode": template.mode,
            "fingerprint": template.fingerprint(),
        },
    )
    return app


def build_from_env(env: Mapping[str, str] | None = None, **overrides: Any) -> Glosa:
    """Construye el sistema con la configuración del entorno (SPEC §17.3)."""
    env = os.environ if env is None else env
    dirs = [d for d in env.get("GLOSA_TEMPLATE_DIRS", "").split(os.pathsep) if d]
    template = load_template(env.get("GLOSA_TEMPLATE", DEFAULT_TEMPLATE), search_dirs=dirs)
    return build_app(
        template,
        data_dir=env.get("GLOSA_DATA_DIR", DEFAULT_DATA_DIR),
        worker_id=env.get("GLOSA_WORKER_ID", f"{socket.gethostname()}-{os.getpid()}"),
        lease_seconds=int(env.get("GLOSA_WORKER_LEASE_SECONDS", DEFAULT_LEASE_SECONDS)),
        **overrides,
    )
