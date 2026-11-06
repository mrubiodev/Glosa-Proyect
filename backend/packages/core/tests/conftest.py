import pytest

from glosa_core.authorization import AuthorizationService
from glosa_core.domain import Role
from glosa_core.testing import COL_A, COL_B, FixedClock, InMemoryAccessRepository



@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def access():
    repo = InMemoryAccessRepository()
    repo.add_member("ana", COL_A, Role.OWNER)
    repo.add_member("edu", COL_A, Role.EDITOR)
    repo.add_member("rita", COL_A, Role.READER)
    repo.add_member("otro", COL_B, Role.OWNER)
    return repo


@pytest.fixture
def authz(access):
    return AuthorizationService(access)


@pytest.fixture
def world():
    from glosa_core.testing_world import World

    return World()
