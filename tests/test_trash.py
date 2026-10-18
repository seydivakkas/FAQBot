"""v1.6: Geri alınabilir SSS silme, çöp kutusu ve veri bütünlüğü."""
import sqlite3

from fastapi.testclient import TestClient

from app.database import _connect, get_db_path, init_db
from app.main import app


def new_record(question="Çöp kutusu için eşsiz deneme sorusu?"):
    return {
        "question": question,
        "answer": "Bu sorunun açıklayıcı örnek cevabı saklanmalıdır.",
        "category": "destek",
        "alternative_questions": ["Arşivden geri gelecek özel ifade"],
        "source_title": "Test kaynak belgesi",
        "source_url": "https://example.org/source",
        "valid_until": "2099-12-31",
        "verification_status": "verified",
    }


def test_soft_delete_inactive_everywhere_and_restore_original_id(client):
    record = client.post("/faqs", json=new_record()).json()
    faq_id = record["id"]
    assert client.get("/faqs").json()["total"] == 111
    assert client.delete(f"/faqs/{faq_id}").status_code == 204
    assert client.get("/faqs").json()["total"] == 110
    assert all(x["id"] != faq_id for x in client.get("/faqs").json()["faqs"])
    assert all(x["question"] != record["question"]
               for x in client.get("/faqs/export").json()["faqs"])
    answer = client.post("/chat", json={"message": record["question"]}).json()
    assert answer["matched_question"] != record["question"]
    trash = client.get("/faqs/trash").json()
    assert trash["total"] == 1
    item = trash["faqs"][0]
    assert item["id"] == faq_id
    assert item["deleted_at"] is not None
    assert item["answer"] == record["answer"]
    assert item["source_title"] == record["source_title"]
    assert item["source_url"] == record["source_url"]
    assert item["verification_status"] == record["verification_status"]
    assert item["valid_until"] == record["valid_until"]
    assert item["alternative_questions"] == record["alternative_questions"]
    restored = client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm": True})
    assert restored.status_code == 200
    assert restored.json()["id"] == faq_id
    assert restored.json()["answer"] == record["answer"]
    assert client.get("/faqs/trash").json()["total"] == 0
    assert client.get("/faqs").json()["total"] == 111
    chat = client.post("/chat", json={"message": record["question"]}).json()
    assert chat["match_type"] == "exact"
    assert chat["answer"] == record["answer"]


def test_delete_is_idempotent_protected_and_restore_requires_confirmation(client):
    first = client.get("/faqs").json()["faqs"][0]
    faq_id = first["id"]
    assert client.delete(f"/faqs/{faq_id}").status_code == 204
    assert client.delete(f"/faqs/{faq_id}").status_code == 404
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={}).status_code == 422
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm": False}).status_code == 422
    assert client.get("/faqs/trash").json()["total"] == 1
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm": True}).status_code == 200
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm": True}).status_code == 404


def test_deleted_question_cannot_be_edited_or_duplicated(client):
    record = client.post("/faqs", json=new_record()).json()
    faq_id = record["id"]
    assert client.delete(f"/faqs/{faq_id}").status_code == 204
    assert client.put(f"/faqs/{faq_id}", json=new_record()).status_code == 404
    duplicate = client.post("/faqs", json=new_record())
    assert duplicate.status_code == 409
    preview = client.post("/faqs/import/preview", files={
        "file": ("archived.csv",
                 ("question,answer,category\n" +
                  f'"{record["question"]}","Yeni yanıt","destek"\n').encode("utf-8"))
    })
    assert preview.status_code == 200
    assert preview.json()["duplicate"] == 1
    assert preview.json()["ready"] == 0
    assert client.get("/faqs/trash").json()["total"] == 1


def test_restore_conflicting_alternative_is_atomic(client):
    record = client.post("/faqs", json=new_record()).json()
    faq_id = record["id"]
    assert client.delete(f"/faqs/{faq_id}").status_code == 204
    blocker = {
        "question": "Arşiv dışından gelen yeni soru",
        "answer": "Eşleşmeyi engellemek için farklı yanıt",
        "category": "kargo",
        "alternative_questions": [record["alternative_questions"][0]],
    }
    created = client.post("/faqs", json=blocker)
    assert created.status_code == 201
    denied = client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm":True})
    assert denied.status_code == 409
    assert "çakış" in denied.json()["detail"].lower()
    assert client.get("/faqs/trash").json()["total"] == 1
    assert all(x["id"] != faq_id for x in client.get("/faqs").json()["faqs"])
    assert client.delete(f"/faqs/{created.json()['id']}").status_code == 204
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm": True}).status_code == 200


def test_trash_and_restore_survive_app_restart(client):
    record = client.post("/faqs", json=new_record()).json()
    faq_id = record["id"]
    assert client.delete(f"/faqs/{faq_id}").status_code == 204
    assert init_db() == 110
    with _connect() as db:
        old = db.execute("SELECT id, deleted_at FROM faqs WHERE id=?", (faq_id,)).fetchone()
    assert old["id"] == faq_id
    assert old["deleted_at"] is not None
    assert client.get("/faqs/trash").json()["faqs"][0]["id"] == faq_id
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm":True}).status_code == 200
    assert init_db() == 111


def test_all_records_deleted_do_not_reseed(client):
    all_faqs = client.get("/faqs").json()["faqs"]
    for faq in all_faqs:
        assert client.delete(f"/faqs/{faq['id']}").status_code == 204
    assert init_db() == 0
    assert client.get("/faqs").json()["total"] == 0
    assert client.get("/faqs/trash").json()["total"] == len(all_faqs)
    assert client.post("/faqs/trash/1/restore", json={"confirm":True}).status_code == 200
    assert init_db() == 1


def test_previous_schema_upgrade_preserves_user_row(tmp_path, monkeypatch):
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "old.db"))
    with sqlite3.connect(get_db_path()) as db:
        db.execute(
            "CREATE TABLE faqs (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "question TEXT NOT NULL UNIQUE, answer TEXT NOT NULL,"
            "category TEXT NOT NULL, alternative_questions TEXT NOT NULL)"
        )
        db.execute("CREATE TABLE app_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.executemany(
            "INSERT INTO app_metadata(key,value) VALUES (?,?)",
            [("initial_seed_done","1"),("v13_additions_done","1")],
        )
        db.execute(
            "INSERT INTO faqs(question,answer,category,alternative_questions)"
            " VALUES (?,?,?,?)",
            ("Eski özel sorum korunacak mı?", "Eski özel cevabım", "hesap", "[]")
        )
    assert init_db() == 1
    with sqlite3.connect(get_db_path()) as db:
        cols = {x[1] for x in db.execute("PRAGMA table_info(faqs)")}
    assert "deleted_at" in cols
    faq_id = client.get("/faqs").json()["faqs"][0]["id"]
    assert client.delete(f"/faqs/{faq_id}").status_code == 204
    assert init_db() == 0
    assert client.post(f"/faqs/trash/{faq_id}/restore", json={"confirm":True}).status_code == 200
    assert client.get("/faqs").json()["faqs"][0]["answer"] == "Eski özel cevabım"


def test_trash_is_local_only(client, tmp_path, monkeypatch):
    assert client.get("/faqs/trash", headers={"Origin":"https://elsewhere.example"}).status_code == 403
    assert client.post("/faqs/trash/1/restore", json={"confirm":True},
                       headers={"Origin":"https://elsewhere.example"}).status_code == 403
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path / "remote.db"))
    with TestClient(app, base_url="http://example.org") as remote:
        assert remote.get("/faqs/trash").status_code == 403
        assert remote.post("/faqs/trash/1/restore", json={"confirm":True}).status_code == 403


def test_trash_ui_visible(client):
    html = client.get("/app").text
    script = client.get("/static/app.js").text
    for ident in ("trashSection", "trashHeading", "trashSearch", "trashCount",
                  "trashItems", "refreshTrashButton", "trashStatus"):
        assert f'id="{ident}"' in html
    assert 'fetch("/faqs/trash")' in script
    assert '/restore"' in script
    assert 'loadFaqTrash()' in script
    assert "window.confirm(" in script
