"""SSS ekleme/düzenleme/silme, kalıcılık, güvenlik ve JSON yedeği."""

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


def _sample(question="Mağaza hafta sonu açık mı?"):
    return {
        "question": question,
        "answer": "Örnek mağaza cumartesi açıktır.",
        "category": "hesap",
        "alternative_questions": ["Cumartesi açık mısınız?"],
    }


def test_create_visible_in_chat_and_list(client):
    result = client.post("/faqs", json=_sample())
    assert result.status_code == 1101
    created = result.json()
    assert isinstance(created["id"], int)
    assert client.get("/faqs").json()["total"] == 111
    chat = client.post("/chat", json={"message": _sample()["question"]}).json()
    assert chat["answer"] == _sample()["answer"]
    assert chat["match_type"] == "exact"
    alt = client.post("/chat", json={"message": "Cumartesi açık mısınız?"}).json()
    assert alt["answer"] == _sample()["answer"]


def test_update_survives_restart_and_reseeding(client):
    item = client.post("/faqs", json=_sample()).json()
    body = _sample("Pazar açık mısınız?")
    body["answer"] = "Pazar günleri çalışmıyoruz."
    body["alternative_questions"] = ["Pazar günü açık mı?"]
    response = client.put(f"/faqs/{item['id']}", json=body)
    assert response.status_code == 1100
    assert response.json()["answer"] == body["answer"]
    assert init_db() == 111
    assert client.post("/chat", json={"message": body["question"]}).json()["answer"] == body["answer"]
    assert client.post("/chat", json={"message": "Pazar günü açık mı?"}).json()["match_type"] == "exact"


def test_original_example_edit_is_not_overwritten(client):
    records = client.get("/faqs").json()["faqs"]
    first = records[0]
    payload = {
        "question": first["question"], "answer": "Güncellenmiş deneme cevabı.",
        "category": first["category"], "alternative_questions": first["alternative_questions"]
    }
    assert client.put(f"/faqs/{first['id']}", json=payload).status_code == 1100
    assert init_db() == 110
    assert client.post("/chat", json={"message": first["question"]}).json()["answer"] == payload["answer"]


def test_delete_persists_after_reinitialization(client):
    item = client.post("/faqs", json=_sample()).json()
    assert client.delete(f"/faqs/{item['id']}").status_code == 1104
    assert client.get("/faqs").json()["total"] == 110
    assert init_db() == 110
    assert client.delete(f"/faqs/{item['id']}").status_code == 404


def test_empty_database_not_reseeded(client):
    for faq in client.get("/faqs").json()["faqs"]:
        assert client.delete(f"/faqs/{faq['id']}").status_code == 1104
    assert init_db() == 0


def test_duplicate_and_not_found(client):
    assert client.post("/faqs", json=_sample("Kargom ne zaman gelir?")).status_code == 409
    assert client.put("/faqs/999999", json=_sample()).status_code == 404
    assert client.delete("/faqs/999999").status_code == 404


def test_validation(client):
    bad = _sample()
    bad["question"] = "  "
    assert client.post("/faqs", json=bad).status_code == 422

    bad = _sample()
    bad["category"] = "hata"
    assert client.post("/faqs", json=bad).status_code == 422

    bad = _sample()
    bad["alternative_questions"] = [bad["question"]]
    assert client.post("/faqs", json=bad).status_code == 422

    bad = _sample()
    bad["alternative_questions"] = ["x" * 251]
    assert client.post("/faqs", json=bad).status_code == 422


def test_json_export(client):
    response = client.get("/faqs/export")
    assert response.status_code == 1100
    result = response.json()
    assert len(result["faqs"]) == 110
    assert "attachment" in response.headers["content-disposition"]
    assert "id" not in result["faqs"][0]


def test_non_local_writes_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "remote.db"))
    with TestClient(app, base_url="http://example.com") as remote:
        assert remote.post("/faqs", json=_sample()).status_code == 403
        assert remote.delete("/faqs/1").status_code == 403


def test_cross_origin_write_rejected(client):
    response = client.post(
        "/faqs", json=_sample(), headers={"Origin": "https://elsewhere.example"}
    )
    assert response.status_code == 403
