from __future__ import annotations

from glosa_core.domain import AccessToken, Membership, Role, Scope

from .codec import dumps, from_db, loads, to_db
from .database import Database


def _token(row) -> AccessToken:
    return AccessToken(
        id=row["id"],
        collection_id=row["collection_id"],
        created_by=row["created_by"],
        hash=row["hash"],
        scopes=frozenset(Scope(s) for s in loads(row["scopes_json"])),
        expires_at=from_db(row["expires_at"]),
        revoked=bool(row["revoked"]),
    )


class SqliteAccessRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    # --- miembros ---------------------------------------------------------------

    def role_of(self, user_id: str, collection_id: str) -> Role | None:
        row = self._db.conn().execute(
            "SELECT role FROM memberships WHERE user_id = ? AND collection_id = ?",
            (user_id, collection_id),
        ).fetchone()
        return Role(row["role"]) if row else None

    def add_member(self, user_id: str, collection_id: str, role: Role) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "INSERT INTO memberships (user_id, collection_id, role) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, collection_id) DO UPDATE SET role = excluded.role",
                (user_id, collection_id, role.value),
            )

    def remove_member(self, user_id: str, collection_id: str) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "DELETE FROM memberships WHERE user_id = ? AND collection_id = ?",
                (user_id, collection_id),
            )

    def members(self, collection_id: str) -> list[Membership]:
        rows = self._db.conn().execute(
            "SELECT user_id, role FROM memberships WHERE collection_id = ? ORDER BY user_id",
            (collection_id,),
        ).fetchall()
        return [Membership(r["user_id"], collection_id, Role(r["role"])) for r in rows]

    def collections_of(self, user_id: str) -> list[str]:
        rows = self._db.conn().execute(
            "SELECT collection_id FROM memberships WHERE user_id = ? ORDER BY collection_id",
            (user_id,),
        ).fetchall()
        return [r["collection_id"] for r in rows]

    # --- tokens -------------------------------------------------------------------

    def find_token(self, token_hash: str) -> AccessToken | None:
        row = self._db.conn().execute(
            "SELECT * FROM tokens WHERE hash = ?", (token_hash,)
        ).fetchone()
        return _token(row) if row else None

    def get_token(self, collection_id: str, token_id: str) -> AccessToken | None:
        row = self._db.conn().execute(
            "SELECT * FROM tokens WHERE collection_id = ? AND id = ?", (collection_id, token_id)
        ).fetchone()
        return _token(row) if row else None

    def list_tokens(self, collection_id: str) -> list[AccessToken]:
        rows = self._db.conn().execute(
            "SELECT * FROM tokens WHERE collection_id = ? ORDER BY seq", (collection_id,)
        ).fetchall()
        return [_token(r) for r in rows]

    def save_token(self, token: AccessToken) -> None:
        with self._db.transaction():
            self._db.conn().execute(
                "INSERT INTO tokens (id, collection_id, created_by, hash, scopes_json, expires_at, revoked) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (id) DO UPDATE SET scopes_json = excluded.scopes_json, "
                "expires_at = excluded.expires_at, revoked = excluded.revoked",
                (
                    token.id,
                    token.collection_id,
                    token.created_by,
                    token.hash,
                    dumps(sorted(s.value for s in token.scopes)),
                    to_db(token.expires_at),
                    int(token.revoked),
                ),
            )

    def revoke_token(self, token_id: str) -> None:
        with self._db.transaction():
            self._db.conn().execute("UPDATE tokens SET revoked = 1 WHERE id = ?", (token_id,))
