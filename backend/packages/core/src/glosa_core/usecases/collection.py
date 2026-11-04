from __future__ import annotations

from ..context import RequestContext
from ..domain import ActorKind, Collection, CollectionSettings, Outcome, Role
from ..errors import InvalidRequest, PermissionDenied
from ..kernel import Kernel
from ..ports import AccessRepository, CollectionRepository
from .base import UseCase

MAX_NAME_LENGTH = 120


class CreateCollection(UseCase):
    """Crea una colección y hace propietario a quien la crea. Solo usuarios, no tokens."""

    action = "collection.create"

    def __init__(
        self,
        kernel: Kernel,
        collections: CollectionRepository,
        access: AccessRepository,
        default_settings: CollectionSettings | None = None,
    ) -> None:
        super().__init__(kernel)
        self._collections = collections
        self._access = access
        self._defaults = default_settings or CollectionSettings()

    def execute(self, ctx: RequestContext, name: str) -> Collection:
        started = self.k.clock.now()
        if ctx.actor.kind is not ActorKind.USER:
            reason = "solo los usuarios pueden crear colecciones"
            self.k.recorder.record(
                ctx,
                self.action,
                Outcome.DENIED,
                details={"permission": "create_collection", "reason": reason},
            )
            raise PermissionDenied("create_collection", reason)

        with self._guard(ctx, self.action, None, started):
            clean = (name or "").strip()
            if not clean or len(clean) > MAX_NAME_LENGTH:
                raise InvalidRequest(f"El nombre debe tener entre 1 y {MAX_NAME_LENGTH} caracteres")

        collection = Collection(
            id=self.k.ids.new_id("col"),
            name=clean,
            created_at=self.k.clock.now(),
            settings=self._defaults,
        )
        self._collections.add(collection)
        self._access.add_member(ctx.actor.id, collection.id, Role.OWNER)
        self.k.recorder.record(
            ctx,
            self.action,
            Outcome.SUCCEEDED,
            collection_id=collection.id,
            target={"collection_id": collection.id},
            details={"name": clean},
            started=started,
        )
        return collection
