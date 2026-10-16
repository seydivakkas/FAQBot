"""API testleri kullanıcı veritabanına dokunmaz."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "test-faqbot.db"))
    with TestClient(app) as api_client:
        yield api_client
