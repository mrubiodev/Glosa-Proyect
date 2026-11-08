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


# --- cierre de conexiones ------------------------------------------------------

def test_cada_hilo_tiene_su_conexion_y_close_las_cierra_todas(tmp_path):
    import threading

    db = Database(tmp_path / "g.db")
    barrier = threading.Barrier(4)
    release = threading.Event()
    seen: list = []

    def work():
        seen.append(db.conn())
        barrier.wait()  # los cuatro hilos siguen vivos a la vez, cada uno con su conexión
        release.wait()

    threads = [threading.Thread(target=work) for _ in range(3)]
    for t in threads:
        t.start()
    barrier.wait()
    db.conn()  # y la del hilo principal
    assert db.open_connections() == 4

    db.close()  # desde el hilo principal, cierra también las de los otros hilos
    release.set()
    for t in threads:
        t.join()
    for conn in seen:
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
    assert db.open_connections() == 0


def test_tras_cerrar_la_base_no_se_puede_usar(tmp_path):
    db = Database(tmp_path / "g.db")
    db.close()
    with pytest.raises(RuntimeError, match="cerrada"):
        db.conn()
    with pytest.raises(RuntimeError, match="cerrada"):
        with db.transaction():
            pass


def test_las_conexiones_de_hilos_que_terminan_no_se_acumulan(tmp_path):
    import threading

    db = Database(tmp_path / "g.db")
    for _ in range(20):  # una API con un hilo nuevo por petición
        t = threading.Thread(target=db.conn)
        t.start()
        t.join()
    assert db.open_connections() <= 1  # solo queda, como mucho, la del último hilo en barrerse
    db.close()


def test_cerrar_dos_veces_no_falla(tmp_path):
    db = Database(tmp_path / "g.db")
    db.close()
    db.close()


def test_la_base_en_memoria_tambien_se_cierra():
    db = Database(":memory:")
    db.close()
    with pytest.raises(RuntimeError, match="cerrada"):
        db.conn()
