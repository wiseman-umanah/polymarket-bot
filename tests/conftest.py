import pytest
from unittest.mock import patch
import db as db_module


@pytest.fixture
def temp_db(tmp_path):
    """Patch db.DB_PATH to a temp file and initialise the schema."""
    db_path = str(tmp_path / "test.db")
    with patch("db.DB_PATH", db_path):
        db_module.init_db()
        yield db_module
