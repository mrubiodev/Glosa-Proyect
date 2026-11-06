"""Esquema de la base de datos, en migraciones numeradas.

`PRAGMA user_version` guarda cuántas se han aplicado. Para cambiar el esquema se AÑADE una
migración al final; las anteriores no se tocan nunca.
"""

MIGRATIONS: list[str] = [
    # --- 1: esquema inicial ---------------------------------------------------
    """
    CREATE TABLE collections (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        settings_json TEXT NOT NULL
    );

    CREATE TABLE memberships (
        user_id TEXT NOT NULL,
        collection_id TEXT NOT NULL,
        role TEXT NOT NULL,
        PRIMARY KEY (user_id, collection_id)
    );
    CREATE INDEX memberships_by_collection ON memberships (collection_id);

    CREATE TABLE tokens (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL UNIQUE,
        collection_id TEXT NOT NULL,
        created_by TEXT NOT NULL,
        hash TEXT NOT NULL UNIQUE,
        scopes_json TEXT NOT NULL,
        expires_at TEXT,
        revoked INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX tokens_by_collection ON tokens (collection_id);

    CREATE TABLE documents (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        collection_id TEXT NOT NULL,
        id TEXT NOT NULL,
        title TEXT NOT NULL,
        source_type TEXT NOT NULL,
        current_version INTEGER NOT NULL,
        status TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        deleted_at TEXT,
        UNIQUE (collection_id, id)
    );

    CREATE TABLE document_versions (
        collection_id TEXT NOT NULL,
        document_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        size INTEGER NOT NULL,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        content BLOB NOT NULL,
        PRIMARY KEY (collection_id, document_id, version)
    );

    CREATE TABLE chunks (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL,
        collection_id TEXT NOT NULL,
        document_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        position INTEGER NOT NULL,
        text TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        UNIQUE (collection_id, id)
    );
    CREATE INDEX chunks_by_document ON chunks (collection_id, document_id, version);

    -- Búsqueda de texto completo sobre `chunks`. `remove_diacritics 2` hace que
    -- "rescision" encuentre "rescisión".
    CREATE VIRTUAL TABLE chunks_fts USING fts5(
        text,
        content = 'chunks',
        content_rowid = 'seq',
        tokenize = 'unicode61 remove_diacritics 2'
    );
    CREATE TRIGGER chunks_after_insert AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts (rowid, text) VALUES (new.seq, new.text);
    END;
    CREATE TRIGGER chunks_after_delete AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts (chunks_fts, rowid, text) VALUES ('delete', old.seq, old.text);
    END;
    CREATE TRIGGER chunks_after_update AFTER UPDATE ON chunks BEGIN
        INSERT INTO chunks_fts (chunks_fts, rowid, text) VALUES ('delete', old.seq, old.text);
        INSERT INTO chunks_fts (rowid, text) VALUES (new.seq, new.text);
    END;

    CREATE TABLE jobs (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL UNIQUE,
        collection_id TEXT NOT NULL,
        type TEXT NOT NULL,
        target TEXT NOT NULL,
        version INTEGER,
        status TEXT NOT NULL,
        actor_json TEXT NOT NULL,
        correlation_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        priority INTEGER NOT NULL,
        attempts INTEGER NOT NULL,
        max_attempts INTEGER NOT NULL,
        run_after TEXT,
        idempotency_key TEXT,
        lease_until TEXT,
        lease_seconds INTEGER,
        error TEXT,
        started_at TEXT,
        finished_at TEXT
    );
    -- La misma clave de idempotencia en la misma colección es la misma petición
    CREATE UNIQUE INDEX jobs_idempotency
        ON jobs (collection_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
    CREATE INDEX jobs_by_status ON jobs (status, priority, seq);
    CREATE INDEX jobs_by_document ON jobs (collection_id, target, status);

    CREATE TABLE operations (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT NOT NULL UNIQUE,
        collection_id TEXT,
        at TEXT NOT NULL,
        correlation_id TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        actor_json TEXT NOT NULL,
        channel TEXT NOT NULL,
        action TEXT NOT NULL,
        outcome TEXT NOT NULL,
        target_json TEXT NOT NULL,
        duration_ms INTEGER,
        details_json TEXT NOT NULL,
        prev_hash TEXT NOT NULL,
        hash TEXT NOT NULL
    );
    CREATE INDEX operations_by_collection ON operations (collection_id, seq);
    CREATE INDEX operations_by_correlation ON operations (collection_id, correlation_id);
    """,
]
