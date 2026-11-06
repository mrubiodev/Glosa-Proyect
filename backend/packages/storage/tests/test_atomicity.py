"""Lo que se escribe junto se confirma junto: un fallo a medias no deja nada a medias.

Estas pruebas solo tienen sentido con SQLite; los dobles en memoria no tienen rollback.
"""
import pytest

from glosa_core.domain import DocumentStatus, JobStatus
from glosa_core.testing import FixedClock
from glosa_core.testing_world import World
from glosa_storage.testing import make_adapters


class FlakyQueue:
    """Delega en la cola real, pero puede fallar al encolar."""

    def __init__(self, real):
        self._real = real
        self.fail_enqueue = False

    def __getattr__(self, name):
        return getattr(self._real, name)

    def enqueue(self, job):
        if self.fail_enqueue:
            raise RuntimeError("se cayó la cola")
        return self._real.enqueue(job)


class FlakyIndex:
    """Delega en el índice real, pero puede fallar DESPUÉS de haber escrito los fragmentos."""

    def __init__(self, real):
        self._real = real
        self.fail_after_writing = False

    def __getattr__(self, name):
        return getattr(self._real, name)

    def index(self, chunks):
        self._real.index(chunks)
        if self.fail_after_writing:
            raise RuntimeError("el índice falló a medias")


def sqlite_world(**wrappers) -> World:
    clock = FixedClock()
    adapters = make_adapters(clock)
    for key, wrapper in wrappers.items():
        adapters[key] = wrapper(adapters[key])
    return World(adapters=adapters, clock=clock)


def table_count(world, table) -> int:
    return world.uow.conn().execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_si_falla_el_encolado_no_queda_ni_el_documento_ni_la_version_ni_el_registro():
    w = sqlite_world(queue=FlakyQueue)
    ana = w.user("ana")
    col = w.new_collection("ana")
    w.queue.fail_enqueue = True

    with pytest.raises(RuntimeError):
        w.upload(ana, col.id, "texto del documento")

    assert w.documents.list(col.id) == []
    assert table_count(w, "document_versions") == 0
    assert table_count(w, "jobs") == 0
    assert [e for e in w.log.entries(col.id) if e.action == "document.submit"] == []
    # y el sistema sigue funcionando después del fallo
    w.queue.fail_enqueue = False
    assert w.upload(ana, col.id, "ahora sí").job is not None
    assert len(w.documents.list(col.id)) == 1


def test_si_falla_el_encolado_de_una_modificacion_no_queda_la_version_nueva():
    w = sqlite_world(queue=FlakyQueue)
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, "versión uno")
    w.run_jobs()

    w.queue.fail_enqueue = True
    with pytest.raises(RuntimeError):
        w.upload(ana, col.id, "versión dos", document_id=res.document_id)

    assert [v.version for v in w.documents.history(col.id, res.document_id)] == [1]
    w.queue.fail_enqueue = False
    again = w.upload(ana, col.id, "versión dos", document_id=res.document_id)
    assert again.version == 2  # la numeración no se saltó ninguna


def test_si_el_indice_falla_a_medias_no_quedan_fragmentos_y_el_trabajo_se_reintenta():
    w = sqlite_world(index=FlakyIndex)
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, "uno.\n\ndos.\n\ntres.")

    w.index.fail_after_writing = True
    job = w.process.execute()

    assert job.status is JobStatus.QUEUED and "falló a medias" in job.error
    assert w.index.all_chunks(col.id) == []  # lo escrito antes del fallo se deshizo
    assert "document.index" not in [e.action for e in w.log.entries(col.id)]
    assert w.documents.get(col.id, res.document_id).status is DocumentStatus.FAILED

    w.index.fail_after_writing = False
    w.clock.advance(seconds=31)  # pasa la espera del reintento
    assert w.process.execute().status is JobStatus.SUCCEEDED
    assert len(w.index.all_chunks(col.id)) == 3
    assert w.documents.get(col.id, res.document_id).status is DocumentStatus.READY


def test_si_una_modificacion_falla_a_medias_el_documento_sigue_sirviendo_la_version_vigente():
    w = sqlite_world(index=FlakyIndex)
    ana = w.user("ana")
    col = w.new_collection("ana")
    res = w.upload(ana, col.id, "precio cien euros")
    w.run_jobs()
    w.upload(ana, col.id, "precio doscientos euros", document_id=res.document_id)

    w.index.fail_after_writing = True
    w.process.execute()

    doc = w.documents.get(col.id, res.document_id)
    assert doc.status is DocumentStatus.READY and doc.current_version == 1
    assert len(w.search.execute(w.ctx(ana), col.id, "cien")) == 1  # la vieja sigue ahí
    assert w.search.execute(w.ctx(ana), col.id, "doscientos") == []  # la nueva no se coló
