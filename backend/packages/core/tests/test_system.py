from datetime import timezone

from glosa_core.system import SystemClock, UuidIds


def test_el_reloj_real_devuelve_hora_con_zona():
    now = SystemClock().now()
    assert now.tzinfo is timezone.utc


def test_los_ids_reales_son_unicos_y_llevan_prefijo():
    ids = UuidIds()
    generated = {ids.new_id("doc") for _ in range(1000)}
    assert len(generated) == 1000
    assert all(i.startswith("doc-") and len(i) == 16 for i in generated)
