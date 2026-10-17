"""Eşik ayarı, tekrar adayları ve kullanıcı onaylı veri kaybı önlemeli birleştirme."""
import json

from fastapi.testclient import TestClient

from app.database import _connect, init_db
from app.duplicates import DEFAULT_DUPLICATE_THRESHOLD
from app.main import app


def make(question, category="siparis", answer="Kayıtlı cevap", alternatives=None):
    return {
        "question": question,
        "answer": answer,
        "category": category,
        "alternative_questions": alternatives or [],
    }


def add_pair(client, different_category=False):
    shared = "Bu örnek teslimat işlemini nasıl takip edebilirim?"
    left = client.post("/faqs", json=make(
        "Yeni teslimat takip ihtiyacı A",
        answer="A sorusunun güvenilir cevabı",
        alternatives=[shared],
    ))
    right = client.post("/faqs", json=make(
        "Yeni teslimat takip ihtiyacı B",
        category="kargo" if different_category else "siparis",
        answer="B sorusunun farklı cevabı",
        alternatives=[shared],
    ))
    assert left.status_code == right.status_code == 201
    return left.json(), right.json()


def find_pair(client, a, b):
    res = client.get("/faqs/duplicates")
    assert res.status_code == 200
    for pair in res.json()["candidates"]:
        if {pair["left"]["id"], pair["right"]["id"]} == {a["id"], b["id"]}:
            return pair
    raise AssertionError("Eklenen çift aday listesinde yok")


def merge_payload(pair, keep_id=None):
    left, right = pair["left"], pair["right"]
    if keep_id is None or keep_id == left["id"]:
        return {
            "keep_id": left["id"], "remove_id": right["id"],
            "expected_keep": pair["left_fingerprint"],
            "expected_remove": pair["right_fingerprint"],
            "confirm": True,
        }
    return {
        "keep_id": right["id"], "remove_id": left["id"],
        "expected_keep": pair["right_fingerprint"],
        "expected_remove": pair["left_fingerprint"],
        "confirm": True,
    }


def test_threshold_default_and_persists(client):
    settings = client.get("/settings/duplicates")
    assert settings.status_code == 200
    assert settings.json()["threshold"] == DEFAULT_DUPLICATE_THRESHOLD
    set_value = client.put("/settings/duplicates", json={"threshold": 0.85})
    assert set_value.status_code == 200
    assert set_value.json()["threshold"] == 0.85
    assert init_db() == 110
    assert client.get("/settings/duplicates").json()["threshold"] == 0.85
    assert client.post("/chat", json={"message": "Kargom ne zaman gelir?"}).json()["match_type"] == "exact"


def test_threshold_validation(client):
    for value in [0.2, 1.0, -1, 0.705, "NaN"]:
        res = client.put("/settings/duplicates", json={"threshold": value})
        assert res.status_code == 422
    assert client.get("/settings/duplicates").json()["threshold"] == 0.70
    assert client.put("/settings/duplicates", json={"threshold": 0.40}).status_code == 200
    assert client.put("/settings/duplicates", json={"threshold": 0.95}).status_code == 200


def test_scan_only_suggests_and_does_not_change_records(client):
    a, b = add_pair(client)
    before = client.get("/faqs").json()["total"]
    pair = find_pair(client, a, b)
    assert pair["score"] == 1.0
    assert pair["can_merge"]
    assert pair["answers_differ"]
    assert len(pair["left_fingerprint"]) == 64
    assert pair["example_left"] == pair["example_right"]
    assert client.get("/faqs").json()["total"] == before
    with _connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM faq_merge_history").fetchone()[0] == 0


def test_explicit_merge_preserves_keep_answer_and_archives_removed(client):
    a, b = add_pair(client)
    candidate = find_pair(client, a, b)
    payload = merge_payload(candidate, keep_id=b["id"])
    res = client.post("/faqs/duplicates/merge", json=payload)
    assert res.status_code == 200
    output = res.json()
    assert output["kept"]["id"] == b["id"]
    assert output["removed_id"] == a["id"]
    assert output["kept"]["answer"] == b["answer"]
    assert a["question"] in output["kept"]["alternative_questions"]
    assert client.get("/faqs").json()["total"] == 111
    chat = client.post("/chat", json={"message": a["question"]}).json()
    assert chat["answer"] == b["answer"]
    with _connect() as conn:
        row = conn.execute("SELECT * FROM faq_merge_history WHERE id = ?",
                           (output["archive_id"],)).fetchone()
        assert row is not None
        assert json.loads(row["keep_before"])["id"] == b["id"]
        assert json.loads(row["removed_before"])["answer"] == a["answer"]
        assert json.loads(row["keep_after"])["answer"] == b["answer"]


def test_unapproved_merge_rejected(client):
    a, b = add_pair(client)
    candidate = find_pair(client, a, b)
    payload = merge_payload(candidate)
    payload.pop("confirm")
    assert client.post("/faqs/duplicates/merge", json=payload).status_code == 422
    payload["confirm"] = False
    assert client.post("/faqs/duplicates/merge", json=payload).status_code == 422
    assert client.get("/faqs").json()["total"] == 112


def test_stale_pair_conflicts_without_deleting(client):
    a, b = add_pair(client)
    candidate = find_pair(client, a, b)
    edited = make(b["question"], answer="Sonradan düzeltilen cevap",
                  alternatives=b["alternative_questions"])
    assert client.put(f"/faqs/{b['id']}", json=edited).status_code == 200
    result = client.post("/faqs/duplicates/merge", json=merge_payload(candidate))
    assert result.status_code == 409
    assert client.get("/faqs").json()["total"] == 112


def test_cross_category_cannot_merge(client):
    a, b = add_pair(client, different_category=True)
    pair = find_pair(client, a, b)
    assert not pair["can_merge"]
    assert not pair["same_category"]
    assert client.post("/faqs/duplicates/merge", json=merge_payload(pair)).status_code == 409
    assert client.get("/faqs").json()["total"] == 112


def test_too_many_alternatives_prevents_merge(client):
    shared = "Ortak farklı kayıt ifadesi"
    a = client.post("/faqs", json=make(
        "Çok alternatifli ana soru",
        alternatives=[shared, *[f"Alternatif ifade no {i}" for i in range(14)]],
    )).json()
    b = client.post("/faqs", json=make(
        "Çok alternatifli ikinci soru", alternatives=[shared],
    )).json()
    pair = find_pair(client, a, b)
    r = client.post("/faqs/duplicates/merge", json=merge_payload(pair))
    assert r.status_code == 409
    assert client.get("/faqs").json()["total"] == 112


def test_threshold_change_does_not_merge_or_change_chat_threshold(client):
    a, b = add_pair(client)
    assert client.put("/settings/duplicates", json={"threshold": 0.95}).status_code == 200
    pair = find_pair(client, a, b)
    assert pair["score"] >= 0.95
    assert client.get("/faqs").json()["total"] == 112
    assert client.post("/chat", json={"message": "Kargom ne zaman gelir?"}).json()["match_type"] == "exact"


def test_settings_and_merge_local_only(client, tmp_path, monkeypatch):
    a, b = add_pair(client)
    pair = find_pair(client, a, b)
    for url, method, payload in (
        ("/settings/duplicates", "PUT", {"threshold": 0.60}),
        ("/faqs/duplicates/merge", "POST", merge_payload(pair)),
    ):
        result = client.request(method, url, json=payload,
                                headers={"Origin": "https://other.example"})
        assert result.status_code == 403
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "remote.db"))
    with TestClient(app, base_url="https://external.example") as remote:
        assert remote.get("/settings/duplicates").status_code == 403
        assert remote.get("/faqs/duplicates").status_code == 403
        assert remote.put("/settings/duplicates", json={"threshold": 0.6}).status_code == 403


def test_ui_has_editable_threshold_and_review(client):
    html = client.get("/app").text
    javascript = client.get("/static/app.js").text
    for name in (
        "dupThresholdRange", "dupThresholdNumber", "dupThresholdSave",
        "dupScan", "duplicateCandidates", "duplicateStatus",
    ):
        assert f'id="{name}"' in html
    assert "fetch(\"/settings/duplicates\"" in javascript
    assert "fetch(\"/faqs/duplicates\"" in javascript
    assert "mergeDuplicatePair(item, keep, remove)" in javascript
    assert "window.confirm(" in javascript
