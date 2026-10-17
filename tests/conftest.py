"""API testleri kullanıcı veritabanına dokunmaz."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "test-faqbot.db"))
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as api_client:
        yield api_client
