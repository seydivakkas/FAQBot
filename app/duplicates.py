"""Yerel SSS tekrar adayları: TF-IDF, kalıcı eşik ve denetimli birleştirme.

Skor anlamsal olasılık değildir; yalnızca metin benzerliği ölçümüdür.
Birleştirme hiçbir zaman tarama sırasında otomatik çalışmaz.
"""
import hashlib
import json
import sqlite3

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.database import _connect
from app.matching import normalize
from app.semantic import get_settings, similarity_matrix

DEFAULT_DUPLICATE_THRESHOLD = 0.70
MIN_DUPLICATE_THRESHOLD = 0.40
MAX_DUPLICATE_THRESHOLD = 0.95


def get_threshold():
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_metadata WHERE key = 'duplicate_threshold'"
        ).fetchone()
    return float(row["value"]) if row is not None else DEFAULT_DUPLICATE_THRESHOLD


def set_threshold(value):
    if not MIN_DUPLICATE_THRESHOLD <= value <= MAX_DUPLICATE_THRESHOLD:
        raise ValueError("Eşik 0.40 ile 0.95 arasında olmalıdır.")
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_metadata (key, value) VALUES ('duplicate_threshold', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(round(value, 2)),),
        )
    return round(value, 2)


def fingerprint(faq):
    data = {
        name: faq.get(name)
        for name in ("id", "question", "answer", "category", "alternative_questions",
                 "source_title", "source_url", "valid_until", "verification_status", "verified_at")
    }
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _parse(row):
    item = dict(row)
    item["alternative_questions"] = json.loads(item["alternative_questions"])
    return item


def _vectors(faqs):
    phrases, owners = [], []
    for faq in faqs:
        # Tekrar eden cümleleri aynı kayıt içinde bir kez hesaba kat.
        seen = set()
        for text in [faq["question"], *faq.get("alternative_questions", [])]:
            value = normalize(text)
            if value and value not in seen:
                seen.add(value)
                phrases.append(value)
                owners.append(faq["id"])
    return phrases, owners


def detect(faqs, threshold, max_results=100, method="tfidf", model_path=None):
    """Soru ve alternatif ifadeler arasındaki en yüksek hibrit metin benzerliği."""
    if len(faqs) < 2:
        return []
    phrases, owners = _vectors(faqs)
    if len(phrases) < 2:
        return []

    if method in ("embedding", "faqvec_tr", "faqvec_v2"):
        if not model_path:
            raise ValueError("Yerel embedding modeli klasörü belirtilmeli.")
        scores = similarity_matrix(phrases, model_path, method=method)
    elif method == "tfidf":
        char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                               lowercase=False, sublinear_tf=True)
        word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                               token_pattern=r"(?u)\b\w+\b", lowercase=False)
        matrix_c = char.fit_transform(phrases)
        matrix_w = word.fit_transform(phrases)
        scores = 0.7 * cosine_similarity(matrix_c) + 0.3 * cosine_similarity(matrix_w)
    else:
        raise ValueError("Tanımsız eşleştirme yöntemi.")
    np.fill_diagonal(scores, 0.0)

    # En iyi ifade çifti her SSS çifti için tek bir aday üretir.
    best = {}
    for i in range(len(phrases)):
        for j in range(i + 1, len(phrases)):
            left, right = owners[i], owners[j]
            if left == right:
                continue
            s = float(scores[i, j])
            if s < threshold:
                continue
            pair = tuple(sorted((left, right)))
            if pair not in best or s > best[pair][0]:
                best[pair] = (s, phrases[i], phrases[j])
    by_id = {faq["id"]: faq for faq in faqs}
    candidates = []
    for (a, b), (score, example_a, example_b) in best.items():
        first, second = by_id[a], by_id[b]
        same_category = first["category"] == second["category"]
        candidates.append({
            "left": first, "right": second,
            "left_fingerprint": fingerprint(first),
            "right_fingerprint": fingerprint(second),
            "score": round(score, 4),
            "method": method,
            "example_left": example_a,
            "example_right": example_b,
            "same_category": same_category,
            "can_merge": same_category,
            "answers_differ": normalize(first["answer"]) != normalize(second["answer"]),
        })
    candidates.sort(key=lambda item: (-item["score"], item["left"]["id"], item["right"]["id"]))
    return candidates[:max_results]


class MergeConflict(ValueError):
    pass


def merge_records(keep_id, other_id, expected_keep, expected_other, approved):
    """İki farklı kaydı ancak açık onaydan sonra atomik birleştir.

    Tam iki kayıt + birleşme öncesi/sonrası bilgilerini arşive kaydeder.
    Korunan kaydın cevabı değiştirilmez, diğer cevap arşivlenir.
    """
    if not approved:
        raise ValueError("Birleştirme için açık onay gerekiyor.")
    if keep_id == other_id:
        raise ValueError("Aynı kayıt kendi kendisiyle birleştirilemez.")
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT id, question, answer, category, alternative_questions, source_title, source_url, valid_until, verification_status, verified_at "
            "FROM faqs WHERE id IN (?, ?) AND deleted_at IS NULL", (keep_id, other_id)
        ).fetchall()
        indexed = {row["id"]: _parse(row) for row in rows}
        if len(indexed) != 2:
            raise MergeConflict("Kayıt silinmiş veya bulunamıyor. Listeyi yenileyin.")
        keep, other = indexed[keep_id], indexed[other_id]
        if fingerprint(keep) != expected_keep or fingerprint(other) != expected_other:
            raise MergeConflict("Kayıtlardan biri değişmiş. Adayları yeniden tarayın.")
        if keep["category"] != other["category"]:
            raise MergeConflict("Farklı kategorideki kayıtlar otomatik birleştirilemez.")

        # Birleştirme sırasında eşik tekrar doğrulanmalı.
        all_rows = conn.execute(
            "SELECT id, question, answer, category, alternative_questions, source_title, source_url, valid_until, verification_status, verified_at FROM faqs WHERE deleted_at IS NULL"
        ).fetchall()
        config = get_settings()
        score_rows = detect([_parse(row) for row in all_rows], get_threshold(),
                            max_results=50000, method=config["method"],
                            model_path=config["model_path"])
        score_rows = [row for row in score_rows if {row["left"]["id"], row["right"]["id"]} == {keep_id, other_id}]
        if not score_rows:
            raise MergeConflict("Bu çift kayıtlı benzerlik eşiğinin altında kaldı.")

        # Korunan ana soruyu ve mevcut alternatifleri sakla; diğer soruyu da alternatif yap.
        retained = {normalize(keep["question"])}
        merged_alts = []
        for text in [*keep["alternative_questions"], other["question"],
                     *other["alternative_questions"]]:
            key = normalize(text)
            if key not in retained:
                retained.add(key)
                merged_alts.append(text)
        if len(merged_alts) > 15:
            raise MergeConflict(
                "Birleştirme 15 alternatif ifade sınırını aşıyor. "
                "Önce kayıtları Ayarlar'dan elle düzenleyin."
            )
        # Başka bir kayıtta bulunan herhangi bir ifade yanlış yanıt doğurabilir.
        rows_all = conn.execute(
            "SELECT id, question, alternative_questions FROM faqs WHERE deleted_at IS NULL "
            "AND id NOT IN (?, ?)", (keep_id, other_id)
        ).fetchall()
        occupied = {
            normalize(text)
            for row in rows_all
            for text in [row["question"], *json.loads(row["alternative_questions"])]
        }
        if retained & occupied:
            raise MergeConflict("Birleşim başka bir SSS kaydının ifadeleriyle çakışıyor.")
        after = {**keep, "alternative_questions": merged_alts}
        archive = conn.execute(
            "INSERT INTO faq_merge_history "
            "(keep_id, removed_id, keep_before, removed_before, keep_after) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                keep_id, other_id, json.dumps(keep, ensure_ascii=False),
                json.dumps(other, ensure_ascii=False),
                json.dumps(after, ensure_ascii=False),
            ),
        )
        conn.execute("UPDATE faqs SET alternative_questions=? WHERE id=?",
                     (json.dumps(merged_alts, ensure_ascii=False), keep_id))
        conn.execute("UPDATE faqs SET deleted_at=CURRENT_TIMESTAMP WHERE id=? AND deleted_at IS NULL", (other_id,))
        # context manager commits on exit; exception rolls back all changes.
    return {"kept": after, "removed_id": other_id, "archive_id": archive.lastrowid}
