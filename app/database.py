"""SQLite veritabanı: ilk kurulum verisi ve kalıcı SSS yönetimi."""

import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "faqs.json"
V13_DATA_PATH = ROOT / "data" / "faqs_v13_additions.json"
CATEGORIES = ("kargo", "iade", "odeme", "hesap", "siparis", "urun", "kampanya", "destek")


def get_db_path() -> Path:
    value = os.environ.get("FAQBOT_DB_PATH")
    return Path(value).expanduser() if value else ROOT / "faqbot.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _as_faq(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["alternative_questions"] = json.loads(item["alternative_questions"])
    return item


def init_db() -> int:
    """Örnekleri SADECE bir kez yükle; kullanıcı düzenlemelerini koru.

    Önceden mevcut faqs tablosu için de meta bayrağı oluşturur.
    Tamamı silinse bile tekrar örnek kayıt eklemez.
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL UNIQUE,
                answer TEXT NOT NULL,
                category TEXT NOT NULL,
                alternative_questions TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faq_merge_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keep_id INTEGER NOT NULL,
                removed_id INTEGER NOT NULL,
                keep_before TEXT NOT NULL,
                removed_before TEXT NOT NULL,
                keep_after TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        seeded = conn.execute(
            "SELECT value FROM app_metadata WHERE key = 'initial_seed_done'"
        ).fetchone()
        if seeded is None:
            current_count = conn.execute(
                "SELECT COUNT(*) FROM faqs"
            ).fetchone()[0]
            if current_count == 0:
                with DATA_PATH.open("r", encoding="utf-8") as file:
                    examples = json.load(file)
                for faq in examples:
                    conn.execute(
                        """
                        INSERT INTO faqs
                            (question, answer, category, alternative_questions)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            faq["question"], faq["answer"], faq["category"],
                            json.dumps(faq.get("alternative_questions", []), ensure_ascii=False),
                        ),
                    )
            conn.execute(
                "INSERT INTO app_metadata (key, value) VALUES ('initial_seed_done', '1')"
            )

        # v1.3: 90 yeni demo kaydını bir kez ekle, düzenlenmiş verileri ezme.
        # Silinmiş kayıtlar uygulama yeniden açılınca tekrar oluşmaz.
        upgraded = conn.execute(
            "SELECT value FROM app_metadata WHERE key = 'v13_additions_done'"
        ).fetchone()
        if upgraded is None:
            with V13_DATA_PATH.open("r", encoding="utf-8") as file:
                additions = json.load(file)
            for faq in additions:
                conn.execute(
                    "INSERT OR IGNORE INTO faqs "
                    "(question, answer, category, alternative_questions) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        faq["question"], faq["answer"], faq["category"],
                        json.dumps(faq.get("alternative_questions", []), ensure_ascii=False),
                    ),
                )
            conn.execute(
                "INSERT INTO app_metadata (key, value) VALUES ('v13_additions_done', '1')"
            )

        return conn.execute("SELECT COUNT(*) FROM faqs").fetchone()[0]


def load_faqs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, question, answer, category, alternative_questions "
            "FROM faqs ORDER BY id"
        ).fetchall()
    return [_as_faq(row) for row in rows]


def get_faq(faq_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, question, answer, category, alternative_questions "
            "FROM faqs WHERE id = ?", (faq_id,)
        ).fetchone()
    return _as_faq(row) if row is not None else None


def add_faq(question: str, answer: str, category: str, alternatives: list[str]) -> dict:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO faqs (question, answer, category, alternative_questions) "
            "VALUES (?, ?, ?, ?)",
            (question, answer, category, json.dumps(alternatives, ensure_ascii=False)),
        )
        faq_id = cursor.lastrowid
    return get_faq(faq_id)


def update_faq(
    faq_id: int, question: str, answer: str, category: str, alternatives: list[str]
) -> dict | None:
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE faqs SET question = ?, answer = ?, category = ?, "
            "alternative_questions = ? WHERE id = ?",
            (question, answer, category, json.dumps(alternatives, ensure_ascii=False), faq_id),
        )
        changed = cursor.rowcount > 0
    return get_faq(faq_id) if changed else None


def delete_faq(faq_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
        return cursor.rowcount > 0


if __name__ == "__main__":
    print(f"Veritabanı hazır! Toplam {init_db()} SSS kaydı var.")
