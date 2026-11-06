import pytest

from glosa_core.testing import FixedClock
from glosa_storage import Database


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def db():
    return Database(":memory:")


@pytest.fixture
def file_db(tmp_path):
    database = Database(tmp_path / "glosa.db")
    yield database
    database.close()
