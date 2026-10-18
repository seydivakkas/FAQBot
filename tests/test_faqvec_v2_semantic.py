"""E5 türevi FAQVec v0.2 seçiminin API ve önek akışı; harici model indirmez."""
import json
import numpy as np
from app import semantic


def test_v2_selection_requires_local_trained_manifest(client, tmp_path):
    directory = tmp_path / "none"
    response = client.put("/settings/semantic", json={
        "method": "faqvec_v2", "model_path": str(directory)
    })
    assert response.status_code == 422
    assert client.get("/settings/semantic").json()["method"] == "tfidf"


def test_v2_selection_and_symmetric_e5_prefix(client, tmp_path, monkeypatch):
    directory = tmp_path / "trained-v2"
    directory.mkdir()
    (directory / "modules.json").write_text("[]", encoding="utf-8")
    (directory / "faqvec_v2_manifest.json").write_text(json.dumps({
        "backbone": {"declared_license": "MIT"},
        "model_input_prefix": "query: ",
        "commercial_acceptance": "HOLD",
    }), encoding="utf-8")
    monkeypatch.setattr(semantic, "model_status", lambda path: {
        "ready_to_load": True, "path_exists": True, "dependency_installed": True
    })

    seen = []
    class FakeLocalModel:
        def encode(self, texts, **kwargs):
            seen.extend(texts)
            # Yalnızca uçtan uca aktarımı sınamak için sentetik vektörler.
            return np.asarray([
                [1.0, 0.1] if "kargo" in text else [0.1, 1.0]
                for text in texts
            ], dtype=np.float32)

    monkeypatch.setattr(semantic, "_get_model", lambda _: FakeLocalModel())
    saved = client.put("/settings/semantic", json={
        "method": "faqvec_v2", "model_path": str(directory)
    })
    assert saved.status_code == 200
    assert saved.json()["method"] == "faqvec_v2"
    assert saved.json()["ready_to_load"] is True
    scan = client.get("/faqs/duplicates")
    assert scan.status_code == 200
    assert scan.json()["method"] == "faqvec_v2"
    assert seen and all(text.startswith("query: ") for text in seen)
    assert client.post("/chat", json={
        "message": "Kargom ne zaman gelir?"
    }).json()["match_type"] == "exact"


def test_v2_bad_origin_does_not_activate(client, tmp_path, monkeypatch):
    directory = tmp_path / "untrusted"
    directory.mkdir()
    (directory / "modules.json").write_text("[]", encoding="utf-8")
    (directory / "faqvec_v2_manifest.json").write_text(json.dumps({
        "backbone": {"declared_license": "UNKNOWN"},
        "model_input_prefix": "query: "
    }), encoding="utf-8")
    monkeypatch.setattr(semantic, "model_status", lambda _: {
        "ready_to_load": True, "path_exists": True, "dependency_installed": True
    })
    response = client.put("/settings/semantic", json={
        "method": "faqvec_v2", "model_path": str(directory)
    })
    assert response.status_code == 422
    assert client.get("/settings/semantic").json()["method"] == "tfidf"
