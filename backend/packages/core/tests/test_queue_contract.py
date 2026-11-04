"""La cola en memoria cumple el contrato. Los adaptadores reales deben pasar los mismos."""
import pytest

from glosa_core.queue_contract import ALL_CHECKS
from glosa_core.testing import InMemoryJobQueue


@pytest.mark.parametrize("check", ALL_CHECKS, ids=lambda c: c.__name__)
def test_contrato_de_la_cola(check):
    check(lambda clock: InMemoryJobQueue(clock))
