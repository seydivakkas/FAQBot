"""Gönüllü yerel sohbet günlüğü, insan incelemesi ve model kıyaslama sözleşmesi."""
import hashlib
import numpy as np

from fastapi.testclient import TestClient

from app import reviews
from app.database import _connect
from app.semantic import EmbeddingUnavailable
from app.main import app


def enable(client):
    response = client.put("/reviews/settings", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def records(client):
    result = client.get("/reviews")
    assert result.status_code == 200
    return result.json()


def test_logging_is_off_by_default(client):
    response = client.get("/reviews/settings")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert client.post("/chat", json={"message": "Kargom ne zaman gelir?"}).status_code == 200
    assert records(client)["total"] == 0


def test_enabled_chat_records_snapshot_method_score_answer(client):
    enable(client)
    chat = client.post("/chat", json={"message": "Kargom ne zaman gelir?"}).json()
    data = records(client)
    assert data["total"] == 1
    item = data["rows"][0]
    assert item["question"] == "Kargom ne zaman gelir?"
    assert item["matched_faq_id"] is not None
    assert item["matched_question"] == chat["matched_question"]
    assert item["answer"] == chat["answer"]
    assert item["match_method"] == "exact"
    assert item["match_score"] == 1.0
    assert item["review_status"] == "pending"
    assert "created_at" in item
    assert not {"ip", "session_id", "email"} & set(item)


def test_fallback_is_logged_and_reviewed_as_correct(client):
    enable(client)
    answer = client.post("/chat", json={
        "message": "zzzzzzzz qqqqqqqq xxxxxxx 9999"
    }).json()
    assert answer["match_type"] == "none"
    item = records(client)["rows"][0]
    assert item["matched_faq_id"] is None
    assert item["match_score"] == 0.0
    labeled = client.patch(f"/reviews/{item['id']}", json={"status": "correct"})
    assert labeled.status_code == 200
    assert labeled.json()["expected_faq_id"] is None
    result = client.post("/reviews/evaluate", json={}).json()
    assert result["compared"] == 1
    assert result["tfidf"]["accuracy"] == 1.0


def test_sensitive_input_is_never_logged(client):
    enable(client)
    for message in (
        "Benim e-postam test@example.com",
        "Numaram 0555 123 45 67",
        "Bana https://example.org/secret adresinden ulaşın",
        "Parola: deneme123",
    ):
        assert client.post("/chat", json={"message": message}).status_code == 200
    assert records(client)["total"] == 0


def test_disable_logging_stops_new_records(client):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    assert client.put("/reviews/settings", json={"enabled": False}).status_code == 200
    client.post("/chat", json={"message": "İade nasıl yapılır?"})
    assert records(client)["total"] == 1


def test_review_correct_and_reset(client):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    item = records(client)["rows"][0]
    response = client.patch(f"/reviews/{item['id']}", json={
        "status": "correct", "note": "Bağımsız olarak inceledim"
    })
    assert response.status_code == 200
    assert response.json()["expected_faq_id"] == item["matched_faq_id"]
    assert response.json()["reviewed_at"] is not None
    assert records(client)["counts"]["correct"] == 1
    pending = client.patch(f"/reviews/{item['id']}", json={"status": "pending"})
    assert pending.status_code == 200
    assert pending.json()["expected_faq_id"] is None
    assert pending.json()["reviewed_at"] is None
    assert records(client)["counts"]["pending"] == 1


def test_incorrect_label_selects_faq_or_fallback(client):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    item = records(client)["rows"][0]
    wrong_id = next(x["id"] for x in client.get("/faqs").json()["faqs"]
                    if x["id"] != item["matched_faq_id"])
    changed = client.patch(f"/reviews/{item['id']}", json={
        "status": "incorrect", "expected_faq_id": wrong_id
    })
    assert changed.status_code == 200
    assert changed.json()["expected_faq_id"] == wrong_id
    data = client.post("/reviews/evaluate", json={"include_embedding": False}).json()
    assert data["tfidf"]["accuracy"] == 0.0
    assert data["embedding"]["status"] == "not_requested"
    no_answer = client.patch(f"/reviews/{item['id']}", json={
        "status": "incorrect", "expected_faq_id": None
    })
    assert no_answer.status_code == 200


def test_invalid_labels_are_rejected(client):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    item = records(client)["rows"][0]
    for bad in (
        {"status":"incorrect", "expected_faq_id":item["matched_faq_id"]},
        {"status":"incorrect", "expected_faq_id":9999999},
        {"status":"correct", "expected_faq_id":9999999},
        {"status":"unknown"},
    ):
        res = client.patch(f"/reviews/{item['id']}", json=bad)
        assert res.status_code in (409, 422)
    assert client.patch("/reviews/10000000", json={"status":"correct"}).status_code == 404
    assert records(client)["counts"]["pending"] == 1


def test_fallback_incorrect_must_have_expected_faq(client):
    enable(client)
    client.post("/chat", json={"message": "zzzzzzzz qqqqqqqq xxxxxxx 9999"})
    item = records(client)["rows"][0]
    response = client.patch(f"/reviews/{item['id']}", json={"status":"incorrect"})
    assert response.status_code == 422
    faq_id = client.get("/faqs").json()["faqs"][0]["id"]
    result = client.patch(f"/reviews/{item['id']}", json={
        "status":"incorrect", "expected_faq_id":faq_id
    })
    assert result.status_code == 200
    assert result.json()["expected_faq_id"] == faq_id


def test_review_list_filters_and_limit(client):
    enable(client)
    for text in ("Kargom ne zaman gelir?", "Ürün stokta var mı nasıl öğrenirim?"):
        client.post("/chat", json={"message": text})
    item = records(client)["rows"][0]
    assert client.patch(f"/reviews/{item['id']}", json={"status":"unsure"}).status_code == 200
    assert client.get("/reviews?status=unsure").json()["counts"]["unsure"] == 1
    assert len(client.get("/reviews?status=unsure").json()["rows"]) == 1
    assert len(client.get("/reviews?limit=1").json()["rows"]) == 1
    assert client.get("/reviews?limit=300").status_code == 422
    assert client.get("/reviews?status=undefined").status_code == 422


def test_historical_snapshot_survives_faq_edit(client):
    enable(client)
    query = "Kargom ne zaman gelir?"
    client.post("/chat", json={"message": query})
    stored = records(client)["rows"][0]
    original = next(x for x in client.get("/faqs").json()["faqs"]
                    if x["id"] == stored["matched_faq_id"])
    payload = {key:original[key] for key in (
        "question", "answer", "category", "alternative_questions",
        "source_title", "source_url", "valid_until", "verification_status"
    )}
    payload["answer"] = "Güncellenmiş cevap, eski kayıt değiştirilmesin."
    assert client.put(f"/faqs/{original['id']}", json=payload).status_code == 200
    assert records(client)["rows"][0]["answer"] == stored["answer"]


def test_evaluate_skips_deleted_ground_truth(client):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    item = records(client)["rows"][0]
    assert client.patch(f"/reviews/{item['id']}", json={"status":"correct"}).status_code == 200
    assert client.delete(f"/faqs/{item['matched_faq_id']}").status_code == 204
    result = client.post("/reviews/evaluate", json={}).json()
    assert result["reviewed"] == 1
    assert result["compared"] == 0
    assert result["skipped_missing_faq"] == 1


def test_embedding_comparison_mocked_offline(client, monkeypatch):
    enable(client)
    query = "Kargom ne zaman gelir?"
    client.post("/chat", json={"message": query})
    item = records(client)["rows"][0]
    assert client.patch(f"/reviews/{item['id']}", json={"status":"correct"}).status_code == 200

    class MockEncoder:
        def encode(self, phrases, **kwargs):
            array = []
            for phrase in phrases:
                digest = hashlib.sha256(phrase.encode("utf-8")).digest()
                v = np.frombuffer(digest, dtype=np.uint8).astype("float32")[:4]
                v /= max(np.linalg.norm(v), 1e-10)
                array.append(v)
            return np.stack(array)

    monkeypatch.setattr(reviews, "_get_model", lambda path: MockEncoder())
    result = client.post("/reviews/evaluate", json={"include_embedding": True}).json()
    assert result["tfidf"]["accuracy"] == 1.0
    assert result["embedding"]["status"] == "ok"
    assert result["embedding"]["accuracy"] == 1.0  # exact override
    assert result["embedding"]["threshold"] == reviews.EMBEDDING_EVAL_THRESHOLD


def test_missing_embedding_model_explained_without_network(client, monkeypatch):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    item = records(client)["rows"][0]
    client.patch(f"/reviews/{item['id']}", json={"status":"correct"})

    def unavailable(_):
        raise EmbeddingUnavailable("Yerel model bulunamadı.")
    monkeypatch.setattr(reviews, "_get_model", unavailable)
    result = client.post("/reviews/evaluate", json={"include_embedding":True}).json()
    assert result["tfidf"]["accuracy"] == 1.0
    assert result["embedding"]["status"] == "unavailable"
    assert "bulunamadı" in result["embedding"]["reason"]


def test_confirm_required_to_erase_history(client):
    enable(client)
    client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    assert client.request("DELETE", "/reviews", json={}).status_code == 422
    assert client.request("DELETE", "/reviews", json={"confirm":False}).status_code == 422
    assert records(client)["total"] == 1
    response = client.request("DELETE", "/reviews", json={"confirm":True})
    assert response.status_code == 200
    assert response.json()["deleted"] == 1
    assert records(client)["total"] == 0


def test_access_controls(client, tmp_path, monkeypatch):
    assert client.put("/reviews/settings", json={"enabled":True}, headers={
        "Origin":"https://attacker.invalid"
    }).status_code == 403
    assert client.get("/reviews", headers={"Origin":"https://attacker.invalid"}).status_code == 403
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "remote.db"))
    with TestClient(app, base_url="https://remote.invalid") as remote:
        assert remote.get("/reviews").status_code == 403
        assert remote.get("/reviews/settings").status_code == 403
        assert remote.post("/reviews/evaluate", json={}).status_code == 403


def test_review_ui_is_exposed(client):
    html = client.get("/app").text
    javascript = client.get("/static/app.js").text
    for attr in (
        "reviewLoggingToggle", "reviewStatusFilter", "reviewRefresh",
        "reviewItems", "reviewDeleteAll", "reviewEvaluate",
        "reviewIncludeEmbedding", "reviewEvaluationResult",
    ):
        assert f'id="{attr}"' in html
    for fragment in ('"/reviews/settings"', '"/reviews/evaluate"',
                     '"/reviews?status="', '"PATCH"', '"DELETE"'):
        assert fragment in javascript
