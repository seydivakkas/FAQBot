"""SSS kayıtlarının SQLite veritabanında saklanması."""

import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "faqs.json"


def get_db_path() -> Path:
    """Testlerde ayrı bir DB kullanabilmek için yolu çalışma anında oku."""
    value = os.environ.get("FAQBOT_DB_PATH")
    return Path(value).expanduser() if value else ROOT / "faqbot.db"


def init_db() -> int:
    """Şema oluştur, JSON örnek verilerini ekle/güncelle. Tekrar çalıştırılabilir."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("r", encoding="utf-8") as file:
        faqs = json.load(file)

    with sqlite3.connect(db_path) as conn:
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
        for faq in faqs:
            conn.execute(
                """
                INSERT INTO faqs
                    (question, answer, category, alternative_questions)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(question) DO UPDATE SET
                    answer = excluded.answer,
                    category = excluded.category,
                    alternative_questions = excluded.alternative_questions
                """,
                (
                    faq["question"],
                    faq["answer"],
                    faq["category"],
                    json.dumps(faq.get("alternative_questions", []), ensure_ascii=False),
                ),
            )
        return conn.execute("SELECT COUNT(*) FROM faqs").fetchone()[0]


def load_faqs() -> list[dict]:
    """Kayıtları uygulamanın ve matcher'ın kullanacağı biçimde döndür."""
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, question, answer, category, alternative_questions
            FROM faqs ORDER BY id
            """
        ).fetchall()

    items = []
    for row in rows:
        item = dict(row)
        item["alternative_questions"] = json.loads(
            item["alternative_questions"]
        )
        items.append(item)
    return items


if __name__ == "__main__":
    print(f"Veritabanı hazır! Toplam {init_db()} SSS kaydı var.")
