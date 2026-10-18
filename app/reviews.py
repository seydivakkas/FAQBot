"""Yerel sohbet eşleşme günlüğü, insan etiketleri ve çevrimdışı kıyaslama.

Kayıt tutma varsayılan olarak KAPALIDIR. IP, oturum, parola veya çerez kaydedilmez.
Kişisel bilgi filtresi yalnızca risk azaltır; tam anonimlik garantisi vermez.
"""
import re
import sqlite3
from datetime import datetime, timezone

import numpy as np

from app.database import _connect, load_faqs
from app.matching import DEFAULT_THRESHOLD, exact_match, find_best_match, normalize
from app.semantic import EmbeddingUnavailable, _get_model, get_settings as semantic_settings

MAX_LOGS = 1000
EVAL_LIMIT = 200
EMBEDDING_EVAL_THRESHOLD = 0.70

# E-posta, URL, telefon/kimlik/kart numarası örüntülerinde soruyu hiç saklama.
_SENSITIVE = (
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"https?://|www\.", re.I),
    re.compile(r"\b(?:\+?\d[\d\s()/-]{8,}\d)\b"),
    re.compile(r"\b(?:şifre|parola|password|otp|doğrulama kodum|tc kimlik)\s*[:=]\s*\S+", re.I),
)


def initialize():
    with _connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_match_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                matched_faq_id INTEGER,
                matched_question TEXT,
                answer TEXT NOT NULL,
                match_method TEXT NOT NULL,
                match_score REAL NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'pending',
                expected_faq_id INTEGER,
                review_note TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_reviews_status "
            "ON chat_match_reviews(review_status, id DESC)"
        )


def get_logging_enabled():
    with _connect() as db:
        row = db.execute(
            "SELECT value FROM app_metadata WHERE key='chat_logging_enabled'"
        ).fetchone()
        return row is not None and row["value"] == "1"


def set_logging_enabled(enabled):
    with _connect() as db:
        db.execute(
            "INSERT INTO app_metadata (key, value) VALUES ('chat_logging_enabled', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("1" if enabled else "0",),
        )
    return enabled


def record_chat(question, match, answer):
    """Sohbet başarılı olsa bile loglama hatası sohbet yanıtını engellememeli."""
    if not get_logging_enabled():
        return False
    if any(pattern.search(question) for pattern in _SENSITIVE):
        return False
    faq = match["faq"] if match else None
    with _connect() as db:
        db.execute(
            "INSERT INTO chat_match_reviews (created_at, question, matched_faq_id, "
            "matched_question, answer, match_method, match_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                question[:500], faq["id"] if faq else None,
                faq["question"] if faq else None, answer[:3000],
                match["match_type"] if match else "none",
                match["match_score"] if match else 0.0,
            ),
        )
        db.execute(
            "DELETE FROM chat_match_reviews WHERE id NOT IN "
            "(SELECT id FROM chat_match_reviews ORDER BY id DESC LIMIT ?)",
            (MAX_LOGS,),
        )
    return True


def list_reviews(status="all", limit=100):
    where, params = ("", []) if status == "all" else ("WHERE review_status=?", [status])
    with _connect() as db:
        counts = db.execute(
            "SELECT review_status, COUNT(*) AS count FROM chat_match_reviews "
            "GROUP BY review_status"
        ).fetchall()
        rows = db.execute(
            "SELECT * FROM chat_match_reviews " + where + " ORDER BY id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    summary = {name: 0 for name in ("pending", "correct", "incorrect", "unsure")}
    for row in counts:
        summary[row["review_status"]] = row["count"]
    return {"total": sum(summary.values()), "counts": summary,
            "rows": [dict(row) for row in rows]}


class ReviewConflict(ValueError):
    pass


def label_review(review_id, status, expected_id=None, note=""):
    if status not in ("pending", "correct", "incorrect", "unsure"):
        raise ValueError("Geçersiz inceleme durumu.")
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            "SELECT * FROM chat_match_reviews WHERE id=?", (review_id,)
        ).fetchone()
        if current is None:
            raise ReviewConflict("İnceleme kaydı bulunamadı.")
        if expected_id is not None:
            exists = db.execute("SELECT 1 FROM faqs WHERE id=?", (expected_id,)).fetchone()
            if exists is None:
                raise ReviewConflict("Beklenen SSS kaydı artık bulunmuyor.")
        if status == "correct":
            if expected_id is not None and expected_id != current["matched_faq_id"]:
                raise ValueError("Doğru etiketi seçildiyse hedef mevcut eşleşme olmalı.")
            expected_id = current["matched_faq_id"]
        elif status == "incorrect":
            # Hedef boş => doğru davranış cevap vermemek olmalı.
            # Yanlış eşleşme none ise mutlaka doğru bir hedef seçilmeli.
            if current["matched_faq_id"] is None and expected_id is None:
                raise ValueError("Yanıt bulunamadığında yanlış etiketi için doğru SSS seçin.")
            if expected_id is not None and expected_id == current["matched_faq_id"]:
                raise ValueError("Yanlış etiketi için farklı SSS ya da yanıtsız seçilmeli.")
        else:
            expected_id = None
        db.execute(
            "UPDATE chat_match_reviews SET review_status=?, expected_faq_id=?, "
            "review_note=?, reviewed_at=? WHERE id=?",
            (
                status, expected_id, note[:500],
                datetime.now(timezone.utc).isoformat() if status in ("correct", "incorrect") else None,
                review_id,
            ),
        )
        row = db.execute("SELECT * FROM chat_match_reviews WHERE id=?", (review_id,)).fetchone()
    return dict(row)


def clear_reviews():
    with _connect() as db:
        count = db.execute("SELECT COUNT(*) AS n FROM chat_match_reviews").fetchone()["n"]
        db.execute("DELETE FROM chat_match_reviews")
    return count


def _actual_reviewed():
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM chat_match_reviews WHERE review_status IN "
            "('correct','incorrect') ORDER BY id DESC LIMIT ?",
            (EVAL_LIMIT,),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def _embedding_predictions(questions, faqs, threshold, model_path, method="embedding"):
    """Sadece doğru/yanlış etiketli soruları güncel bilgi tabanına göre yeniden hesapla."""
    owners, phrases = [], []
    for faq in faqs:
        for phrase in (faq["question"], *faq["alternative_questions"]):
            cleaned = normalize(phrase)
            if cleaned:
                owners.append(faq["id"])
                phrases.append(cleaned)
    if not phrases:
        return [None] * len(questions)
    if method == "faqvec_tr":
        from app.faqvec_tr import OwnModelError, load_model
        try:
            model = load_model(model_path)
        except OwnModelError as exc:
            raise EmbeddingUnavailable(str(exc)) from exc
    else:
        model = _get_model(model_path)
    try:
        raw_vectors = np.asarray(model.encode(
            phrases + [normalize(q) for q in questions],
            convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        ), dtype=np.float32)
    except Exception as exc:
        raise EmbeddingUnavailable("Yerel model, değerlendirme vektörlerini üretemedi.") from exc
    if raw_vectors.ndim != 2 or raw_vectors.shape[0] != len(phrases) + len(questions):
        raise EmbeddingUnavailable("Yerel model beklenmedik boyut üretti.")
    # Modelden normalizasyon beklenir ancak sahte veya uyumsuz modellerde garanti altına al.
    norms = np.linalg.norm(raw_vectors, axis=1, keepdims=True)
    vectors = raw_vectors / np.maximum(norms, 1e-12)
    similarity = vectors[len(phrases):] @ vectors[:len(phrases)].T
    predicted = []
    for query, scores in zip(questions, similarity):
        direct = exact_match(query, faqs)
        if direct:
            predicted.append(direct["id"])
        else:
            i = int(scores.argmax())
            predicted.append(owners[i] if float(scores[i]) >= threshold else None)
    return predicted


def evaluate(include_embedding=False):
    rows = _actual_reviewed()
    faqs = load_faqs()
    active_ids = {faq["id"] for faq in faqs}
    # Değerlendirme hedefi silinmiş SSS artık karşılaştırma için geçerli değildir.
    valid = [r for r in rows if r["expected_faq_id"] is None
             or r["expected_faq_id"] in active_ids]
    skipped = len(rows) - len(valid)
    questions = [r["question"] for r in valid]
    expected = [r["expected_faq_id"] for r in valid]
    tfidf_predictions = []
    for text in questions:
        matched = find_best_match(text, faqs, threshold=DEFAULT_THRESHOLD)
        tfidf_predictions.append(matched["faq"]["id"] if matched else None)

    def metrics(predicted, method, threshold):
        correct = sum(p == goal for p, goal in zip(predicted, expected))
        return {
            "method": method, "total": len(expected), "correct": correct,
            "accuracy": round(correct / len(expected), 4) if expected else None,
            "threshold": threshold,
            "predicted": len([p for p in predicted if p is not None]),
        }

    result = {
        "reviewed": len(rows), "compared": len(valid), "skipped_missing_faq": skipped,
        "tfidf": metrics(tfidf_predictions, "tfidf", DEFAULT_THRESHOLD),
        "embedding": {"status": "not_requested"},
        "note": "İncelenen etiketler ve GÜNCEL bilgi tabanı karşılaştırılır. "
                "Örnekler bağımsız test seti değilse doğruluk genellenemez.",
    }
    if include_embedding:
        settings = semantic_settings()
        try:
            predicted = _embedding_predictions(
                questions, faqs, EMBEDDING_EVAL_THRESHOLD, settings["model_path"],
                method=settings["method"]
            ) if valid else []
            result["embedding"] = {
                "status": "ok",
                **metrics(predicted, settings["method"] if settings["method"] == "faqvec_tr" else "embedding", EMBEDDING_EVAL_THRESHOLD),
            }
        except EmbeddingUnavailable as exc:
            result["embedding"] = {"status": "unavailable", "reason": str(exc)}
    return result
