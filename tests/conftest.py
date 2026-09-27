import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import testenv  # noqa: E402,F401  (must run before app imports)
import pytest  # noqa: E402


@pytest.fixture(scope="session")
def creds():
    return testenv.provision_test_principals()


@pytest.fixture
def clean_ledger(creds):
    from app.database.connection import reset_test_database
    from app.auth import clear_all_sessions
    reset_test_database()
    clear_all_sessions()
    yield


@pytest.fixture
def client(creds):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
