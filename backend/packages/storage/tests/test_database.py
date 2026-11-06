import sqlite3

import pytest

from glosa_storage import Database
from glosa_storage.schema import MIGRATIONS


def count(db, table="collections") -> int:
    return db.conn().execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def insert(db, ident):
    db.conn().execute(
        "INSERT INTO collections (id, name, created_at, settings_json) VALUES (?, 'x', 't', '{}')",
        (ident,),
    )


def test_la_base_nueva_aplica_todas_las_migraciones(db):
    version = db.conn().execute("PRAGMA user_version").fetchone()[0]
    assert version == len(MIGRATIONS)
    tables = {r[0] for r in db.conn().execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"collections", "documents", "document_versions", "chunks", "jobs", "operations",
            "tokens", "memberships", "chunks_fts"} <= tables


def test_abrir_otra_vez_no_repite_migraciones(tmp_path):
    path = tmp_path / "g.db"
    first = Database(path)
    insert(first, "c1")
    first.close()
    second = Database(path)  # no debe fallar ni borrar nada
    assert count(second) == 1
    second.close()


def test_una_base_de_una_version_mas_nueva_se_rechaza(tmp_path):
    path = tmp_path / "g.db"
    raw = sqlite3.connect(path)
    raw.execute(f"PRAGMA user_version = {len(MIGRATIONS) + 5}")
    raw.commit()
    raw.close()
    with pytest.raises(RuntimeError, match="más nueva"):
        Database(path)


def test_la_base_en_archivo_usa_wal(file_db):
    assert file_db.conn().execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_una_transaccion_se_confirma_si_todo_va_bien(db):
    with db.transaction():
        insert(db, "c1")
        insert(db, "c2")
    assert count(db) == 2


def test_una_excepcion_deshace_todo_lo_de_la_transaccion(db):
    with pytest.raises(RuntimeError):
        with db.transaction():
            insert(db, "c1")
            insert(db, "c2")
            raise RuntimeError("falla a mitad")
    assert count(db) == 0


def test_las_transacciones_anidadas_se_unen_a_la_exterior(db):
    with db.transaction():
        insert(db, "c1")
        with db.transaction():
            insert(db, "c2")
        assert count(db) == 2
    assert count(db) == 2


def test_un_fallo_en_una_anidada_deshace_tambien_lo_de_la_exterior(db):
    with pytest.raises(RuntimeError):
        with db.transaction():
            insert(db, "c1")
            with db.transaction():
                insert(db, "c2")
                raise RuntimeError("falla la interior")
    assert count(db) == 0


def test_despues_de_un_fallo_se_puede_abrir_otra_transaccion(db):
    with pytest.raises(RuntimeError):
        with db.transaction():
            insert(db, "c1")
            raise RuntimeError
    with db.transaction():
        insert(db, "c2")
    assert count(db) == 1


def test_los_datos_persisten_tras_cerrar_y_reabrir(tmp_path):
    path = tmp_path / "g.db"
    first = Database(path)
    with first.transaction():
        insert(first, "c1")
    first.close()
    assert count(Database(path)) == 1
