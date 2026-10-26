import os
import tempfile

# Tests use their own database and never call Gemini.
os.environ["WITH_US_DB"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DEMO_MODE"] = "1"
os.environ["GEMINI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

SLUGS = ["meera", "karan", "ramesh", "sunita"]


@pytest.fixture
def seeded():
    seed()
    return True


@pytest.fixture
def as_member(seeded):
    clients = {}

    def get(slug: str) -> TestClient:
        if slug not in clients:
            c = TestClient(app)
            r = c.post("/api/session", json={"code": "meera", "member_id": slug})
            assert r.status_code == 200, r.text
            clients[slug] = c
        return clients[slug]

    return get
