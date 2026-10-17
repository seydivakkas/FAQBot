"""v1.3: 110 örnek SSS ve kullanıcı verisini koruyan bir kerelik genişletme."""

import json
import sqlite3
from collections import Counter

from app.database import DATA_PATH, V13_DATA_PATH, get_db_path, init_db, load_faqs
from app.matching import normalize


def test_seed_content_and_unique_paraphrases():
    originals = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    additions = json.loads(V13_DATA_PATH.read_text(encoding="utf-8"))
    assert len(originals) == 20
    assert len(additions) == 90
    categories = Counter(faq["category"] for faq in [*originals, *additions])
    assert categories == {
        "kargo": 15, "iade": 20, "odeme": 15, "hesap": 10,
        "siparis": 15, "urun": 15, "kampanya": 10, "destek": 10,
    }
    phrases = []
    for faq in [*originals, *additions]:
        assert faq["question"].strip() and len(faq["answer"]) >= 50
        assert len(faq["alternative_questions"]) >= 2
        phrases += [normalize(faq["question"]), *(normalize(q) for q in faq["alternative_questions"])]
    assert len(phrases) == len(set(phrases))


def test_v13_does_not_overwrite_user_changes(client):
    first = client.get("/faqs").json()["faqs"][0]
    payload = {key: first[key] for key in ("question", "category", "alternative_questions")}
    payload["answer"] = "Kullanıcının düzenlediği cevap korunmalıdır."
    assert client.put(f"/faqs/{first['id']}", json=payload).status_code == 200
    assert init_db() == 110
    assert client.post("/chat", json={"message": first["question"]}).json()["answer"] == payload["answer"]


def test_v13_migration_of_existing_v12_database(tmp_path, monkeypatch):
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "old.db"))
    with sqlite3.connect(get_db_path()) as db:
        db.execute(
            "CREATE TABLE faqs (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "question TEXT NOT NULL UNIQUE, answer TEXT NOT NULL, "
            "category TEXT NOT NULL, alternative_questions TEXT NOT NULL)"
        )
        db.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute(
            "INSERT INTO app_metadata (key, value) VALUES ('initial_seed_done', '1')"
        )
        db.execute(
            "INSERT INTO faqs (question, answer, category, alternative_questions) "
            "VALUES (?, ?, ?, ?)", ("Özel kayıt silinmesin", "Özel yanıt", "hesap", "[]")
        )
    assert init_db() == 91  # 1 eski kullanıcı kaydı + 90 yeni kayıt
    assert init_db() == 91
    assert any(x["question"] == "Özel kayıt silinmesin" for x in load_faqs())
    # Yükseltme sonrası silinen soru tekrar eklenmemeli.
    with sqlite3.connect(get_db_path()) as db:
        db.execute("DELETE FROM faqs WHERE question = ?", ("Kargom dağıtıma çıktı ama gelmedi, ne yapabilirim?",))
    assert init_db() == 90


def test_new_topics_are_in_chat(client):
    for question, category in (
        ("Ürün stokta var mı nasıl öğrenirim?", "urun"),
        ("Siparişim alındı mı, nasıl anlayabilirim?", "siparis"),
        ("İndirim kuponunu nasıl kullanırım?", "kampanya"),
        ("Canlı müşteri temsilcisine nasıl bağlanırım?", "destek"),
    ):
        response = client.post("/chat", json={"message": question})
        assert response.status_code == 200
        assert response.json()["category"] == category
        assert response.json()["match_type"] == "exact"
