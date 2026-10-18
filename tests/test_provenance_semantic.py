"""Kaynak/geçerlilik bilgisi ve ağsız yerel embedding iş akışı."""
from datetime import date, timedelta
import hashlib
import numpy as np
from app.database import init_db
from app import semantic


def sample(question="Yeni FAQ kaynağına nasıl ulaşırım?"):
    return {
        "question": question,
        "answer": "Örnek yanıt içeriği; kaynak doğrulaması elle yapılmıştır.",
        "category": "destek",
        "alternative_questions": ["Kaynak bağlantısı nereden bulunur?"],
    }


def test_source_fields_defaults_and_existing_migration(client):
    original = client.get("/faqs").json()["faqs"][0]
    assert original["verification_status"] == "unverified"
    assert original["source_url"] == ""
    assert original["valid_until"] is None
    assert original["validity_status"] == "unspecified"
    assert init_db() == 110
    assert client.get("/faqs").json()["faqs"][0]["source_title"] == ""


def test_source_save_chat_export_and_reopen(client):
    payload = sample()
    payload.update({
        "source_title": "Resmî SSS açıklaması",
        "source_url": "https://example.org/sss",
        "valid_until": (date.today() + timedelta(days=10)).isoformat(),
        "verification_status": "verified",
    })
    added = client.post("/faqs", json=payload)
    assert added.status_code == 201
    record = added.json()
    assert record["verification_status"] == "verified"
    assert record["validity_status"] == "current"
    assert record["verified_at"]
    answer = client.post("/chat", json={"message": payload["question"]}).json()
    assert answer["source_title"] == payload["source_title"]
    assert answer["source_url"] == payload["source_url"]
    assert answer["verification_status"] == "verified"
    exported = client.get("/faqs/export").json()["faqs"]
    match = next(row for row in exported if row["question"] == payload["question"])
    assert match["valid_until"] == payload["valid_until"]
    assert match["source_title"] == payload["source_title"]
    assert init_db() == 111
    reread = next(x for x in client.get("/faqs").json()["faqs"] if x["id"] == record["id"])
    assert reread["verified_at"] == record["verified_at"]


def test_invalid_verification_and_url(client):
    wrong = sample()
    wrong["verification_status"] = "verified"
    assert client.post("/faqs", json=wrong).status_code == 422
    for url in ("javascript:alert(1)", "file:///tmp/source", "example.com", "http://"):
        data = sample()
        data["source_url"] = url
        assert client.post("/faqs", json=data).status_code == 422
    invalid = sample()
    invalid["valid_until"] = "21-12-2026"
    assert client.post("/faqs", json=invalid).status_code == 422


def test_expired_answer_is_marked(client):
    data = sample()
    data.update({
        "source_title": "Arşiv açıklaması",
        "source_url": "https://example.org/arsiv",
        "valid_until": "2000-01-01",
        "verification_status": "verified",
    })
    created = client.post("/faqs", json=data)
    assert created.status_code == 201
    assert created.json()["validity_status"] == "expired"
    response = client.post("/chat", json={"message": data["question"]})
    assert response.status_code == 200
    assert response.json()["validity_status"] == "expired"


def test_edit_resets_previous_verification_when_metadata_removed(client):
    data = sample()
    data.update({
        "source_title": "Belge",
        "source_url": "https://example.org/belge",
        "verification_status": "verified",
    })
    created = client.post("/faqs", json=data).json()
    result = client.put(f"/faqs/{created['id']}", json=sample())
    assert result.status_code == 200
    assert result.json()["verification_status"] == "unverified"
    assert result.json()["verified_at"] is None


def test_import_preserves_source_columns(client):
    import io
    import csv
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "soru", "cevap", "kategori", "kaynak_basligi", "kaynak_url",
        "gecerlilik_tarihi", "dogrulama_durumu",
    ])
    writer.writerow([
        "Yeni kargo hizmeti neden gecikti?", "Kontrol için kargo kaydını inceleyin.",
        "kargo", "Kargo açıklaması", "https://example.org/kargo",
        "2099-01-01", "verified",
    ])
    preview = client.post("/faqs/import/preview", files={
        "file": ("kaynakli.csv", buffer.getvalue().encode("utf-8"), "text/csv")
    })
    assert preview.status_code == 200
    assert preview.json()["ready"] == 1
    item = preview.json()["rows"][0]["data"]
    assert item["source_title"] == "Kargo açıklaması"
    saved = client.post("/faqs/import/commit", json={"records":[item]})
    assert saved.status_code == 200
    record = next(x for x in client.get("/faqs").json()["faqs"]
                  if x["question"] == item["question"])
    assert record["source_url"] == "https://example.org/kargo"
    assert record["verification_status"] == "verified"


def test_semantic_default_and_missing_dependency(client, tmp_path):
    current = client.get("/settings/semantic")
    assert current.status_code == 200
    assert current.json()["method"] == "tfidf"
    assert current.json()["ready_to_load"] is False
    arbitrary = tmp_path / "missing"
    result = client.put("/settings/semantic", json={
        "method": "embedding", "model_path": str(arbitrary),
    })
    assert result.status_code == 422
    assert client.get("/settings/semantic").json()["method"] == "tfidf"
    assert client.get("/faqs/duplicates").status_code == 200


def test_fake_local_encoder_infers_semantic_pair(client, tmp_path, monkeypatch):
    local_model = tmp_path / "local-embedding"
    local_model.mkdir()
    (local_model / "modules.json").write_text("[]", encoding="utf-8")

    def ready(_):
        return {"path_exists":True, "dependency_installed":True, "ready_to_load":True}

    monkeypatch.setattr(semantic, "model_status", ready)

    class FakeEncoder:
        def encode(self, phrases, **_):
            vectors = []
            for phrase in phrases:
                # Two semantically related, lexically unrelated demo questions.
                if phrase in ("paketim kayıp", "gönderim bulunamadı"):
                    vector = np.array([1.0, 0.0, 0.0, 0.0])
                else:
                    digest = hashlib.sha256(phrase.encode("utf-8")).digest()
                    vector = np.frombuffer(digest, dtype=np.uint8).astype(float)[:4] - 127.5
                    vector /= np.linalg.norm(vector)
                vectors.append(vector)
            return np.stack(vectors)

    monkeypatch.setattr(semantic, "_get_model", lambda path: FakeEncoder())
    status = client.put("/settings/semantic", json={
        "method": "embedding", "model_path": str(local_model)
    })
    assert status.status_code == 200
    assert status.json()["method"] == "embedding"
    first = client.post("/faqs", json={
        "question": "Paketim kayıp", "answer": "İlk yanıt", "category": "kargo"
    })
    second = client.post("/faqs", json={
        "question": "Gönderim bulunamadı", "answer": "İkinci yanıt", "category": "kargo"
    })
    assert first.status_code == second.status_code == 201
    res = client.get("/faqs/duplicates")
    assert res.status_code == 200
    assert res.json()["method"] == "embedding"
    target = [
        item for item in res.json()["candidates"]
        if {item["left"]["id"],item["right"]["id"]} ==
            {first.json()["id"],second.json()["id"]}
    ]
    assert target and target[0]["score"] >= 0.99
    # Tarama kayıtları kendi kendine değiştirmez.
    assert client.get("/faqs").json()["total"] == 112
    # Eski sohbet eşleştirme tipi etkilenmez.
    assert client.post("/chat", json={"message":"Kargom ne zaman gelir?"}).json()["match_type"] == "exact"
    assert client.get("/settings/semantic").json()["model_path"] == str(local_model)


def test_bad_model_path_rejected(client):
    for path in ("", "not/absolute/path", "https://example.org/model"):
        res = client.put("/settings/semantic", json={
            "method": "embedding", "model_path": path
        })
        assert res.status_code == 422
    assert client.get("/settings/semantic").json()["method"] == "tfidf"


def test_semantic_provenance_ui_elements(client):
    html = client.get("/app").text
    javascript = client.get("/static/app.js").text
    for item in (
        "editSourceTitle", "editSourceUrl", "editValidUntil", "editVerificationStatus",
        "dupMethod", "dupModelPath", "dupMethodSave", "dupMethodStatus",
    ):
        assert f'id="{item}"' in html
    assert 'fetch("/settings/semantic"' in javascript
    assert "source_title: editSourceTitle.value.trim()" in javascript
