import pytest

from glosa_core.testing_world import World


@pytest.fixture
def world():
    return World()
