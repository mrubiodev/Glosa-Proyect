import threading
import time

import pytest

from glosa_worker import WorkerError, drain, run


def scripted(*results):
    """Una función que devuelve, en orden, lo indicado; una excepción se lanza."""
    queue = list(results)
    calls = []

    def process_next():
        calls.append(1)
        item = queue.pop(0) if queue else None
        if isinstance(item, BaseException):
            raise item
        return item

    process_next.calls = calls
    return process_next


def test_procesa_trabajos_hasta_que_se_pide_parar():
    stop = threading.Event()
    seen = []

    def on_job(job):
        seen.append(job)
        if len(seen) == 3:
            stop.set()

    fn = scripted("a", "b", "c", "d", "e")
    assert run(fn, stop=stop, on_job=on_job) == 3
    assert seen == ["a", "b", "c"]
    assert len(fn.calls) == 3  # no pide un cuarto: paró al terminar el tercero


def test_si_ya_se_pidio_parar_no_empieza_ningun_trabajo():
    stop = threading.Event()
    stop.set()
    fn = scripted("a")
    assert run(fn, stop=stop) == 0
    assert fn.calls == []


def test_sin_trabajo_espera_y_vuelve_a_mirar():
    stop = threading.Event()
    fn = scripted(None, None, "a")
    seen = []

    def on_job(job):
        seen.append(job)
        stop.set()

    assert run(fn, stop=stop, idle_seconds=0.01, on_job=on_job) == 1
    assert len(fn.calls) == 3


def test_la_espera_se_interrumpe_en_cuanto_se_pide_parar():
    stop = threading.Event()
    threading.Timer(0.05, stop.set).start()
    started = time.monotonic()
    assert run(scripted(), stop=stop, idle_seconds=30) == 0  # ¡30 s de espera!
    assert time.monotonic() - started < 2


def test_un_fallo_de_infraestructura_se_avisa_y_se_sigue():
    stop = threading.Event()
    errors = []
    fn = scripted(RuntimeError("base bloqueada"), "a")

    def on_job(job):
        stop.set()

    assert run(fn, stop=stop, idle_seconds=0.01, on_job=on_job, on_error=errors.append) == 1
    assert [str(e) for e in errors] == ["base bloqueada"]


def test_demasiados_fallos_seguidos_hacen_que_el_worker_se_rinda():
    stop = threading.Event()
    fn = scripted(*[RuntimeError(f"fallo {i}") for i in range(10)])
    with pytest.raises(WorkerError, match="3 fallos seguidos"):
        run(fn, stop=stop, idle_seconds=0.001, max_consecutive_errors=3)
    assert len(fn.calls) == 3


def test_un_exito_reinicia_la_cuenta_de_fallos_seguidos():
    stop = threading.Event()
    fn = scripted(RuntimeError("1"), RuntimeError("2"), "ok", RuntimeError("3"), RuntimeError("4"), "ok")
    done = []

    def on_job(job):
        done.append(job)
        if len(done) == 2:
            stop.set()

    # con límite 3 no se rinde: nunca hay 3 fallos SEGUIDOS
    assert run(fn, stop=stop, idle_seconds=0.001, max_consecutive_errors=3, on_job=on_job) == 2


def test_al_pedir_parar_termina_el_trabajo_en_curso_antes_de_salir():
    stop = threading.Event()
    finished = []

    def slow():
        stop.set()  # alguien pide parar mientras este trabajo está en marcha
        time.sleep(0.02)
        finished.append("terminado")
        return "job"

    assert run(slow, stop=stop) == 1
    assert finished == ["terminado"]


def test_drain_procesa_lo_que_haya_y_termina():
    fn = scripted("a", "b", "c", None, "no-debe-llegar")
    assert drain(fn) == 3
    assert len(fn.calls) == 4


def test_drain_con_limite():
    assert drain(scripted("a", "b", "c"), limit=2) == 2
    assert drain(scripted(), limit=5) == 0
