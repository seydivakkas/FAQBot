"""FAQVec D05: yalnız yeni yazılan 24 yardımcı niyet + D03 train bölmesi.

Kaynak Git blob SHA sabittir, farklı kaynak/indirme kabul edilmez.
Genişleme verisi validation/test'e eklenmez; 96'lık D04 test aynen kalır.
Bu veriler AI taslağıdır; bağımsız insan ve ticari kabul içermez.
"""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.matching import normalize
from app.faqvec_v2_data import DatasetError, positive_pairs, validate_intents
from scripts.faqvec_d03_ai_review import evaluate

ROOT = Path(__file__).resolve().parents[1]
AUX_SOURCE = ROOT / "seed" / "faqvec_d05_ozgun_egitim_ekleri_v01.json"
AUX_GIT_BLOB = "b5fbf9135fd286852c4f441fa8e28833ff008d60"
SOURCE_ID = "faqvec-d05-project-authored"


def git_blob_sha(path):
    payload = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode() + b"\0" + payload
    ).hexdigest()


def load_auxiliary_training():
    if git_blob_sha(AUX_SOURCE) != AUX_GIT_BLOB:
        raise DatasetError("D05 özgün veri değişti; yeni köken ve AI incelemesi gerekli.")
    package = json.loads(AUX_SOURCE.read_text(encoding="utf-8"))
    if (package.get("schema_version") != 1 or
            package.get("source_id") != SOURCE_ID or
            package.get("third_party_dataset_used") is not False or
            package.get("commercial_training_approved") is not False or
            package.get("rights_review_complete") is not False or
            package.get("independent_human_review") is not False or
            package.get("role") != "train_only_auxiliary_never_validation_or_test"):
        raise DatasetError("D05 köken ve TRAIN_ONLY sözleşmesi ihlal edildi.")
    base, _revised, _negative, _oos, stats = evaluate()
    validate_intents(base)
    if stats["splits"] != {"train": 74, "validation": 10, "test": 12}:
        raise DatasetError("Önceki D04 train/validation/test bölmesi değişti.")
    used_ids = {item["intent_id"] for item in base}
    known_questions = {
        normalize(question)
        for row in base
        for question in (row["question"], *row["alternatives"])
    }
    rows = package.get("records")
    if not isinstance(rows, list) or len(rows) != 24:
        raise DatasetError("D05 tam 24 özgün niyet içermeli.")
    seen = set()
    families = defaultdict(list)
    for row in rows:
        ident = row.get("intent_id")
        if not ident or ident in used_ids or ident in seen or row.get("split") != "train":
            raise DatasetError("Niyet tekrarı veya test/veri sızıntısı.")
        seen.add(ident)
        if (row.get("source_id") != SOURCE_ID or
                row.get("origin_kind") != "project_authored_ai_draft" or
                row.get("train_only_auxiliary") is not True or
                row.get("commercial_training_approved") is not False or
                row.get("rights_verified") is not False or
                row.get("human_review") != "not_performed"):
            raise DatasetError("Ticari/onay kaynak bayrağı veya köken yanlış.")
        texts = [row.get("question"), *row.get("alternatives", [])]
        if len(texts) != 3 or not isinstance(row.get("answer"), str) or not row["answer"].strip():
            raise DatasetError("D05 iki alternatif ve bir taslak cevap gerektirir.")
        for q in texts:
            if not isinstance(q, str) or not q.strip() or len(q) > 300:
                raise DatasetError("D05 sorgu biçimi geçersiz.")
            key = normalize(q)
            if key in known_questions:
                raise DatasetError("D05 yeni sorusu başka niyet veya mevcut test ile çakışıyor.")
            known_questions.add(key)
        family = row.get("family_id")
        if not isinstance(family, str) or not family.startswith("d05-"):
            raise DatasetError("D05 eğitim ailesi yanlış.")
        families[family].append(row)
    if len(families) != 12 or any(len(group) != 2 for group in families.values()):
        raise DatasetError("Her D05 negatif adayı ailesi iki ayrı niyet taşımalı.")
    return rows


def augmented_positive_pairs():
    base, *_ = evaluate()
    baseline = positive_pairs(base, split="train")
    if len(baseline) != 74:
        raise DatasetError("D04 temel eğitim niyetleri değişmiş.")
    extended = []
    for row in base:
        if row["split"] == "train":
            for alternative in row["alternatives"]:
                extended.append({
                    "anchor": row["question"], "positive": alternative,
                    "intent_id": row["intent_id"],
                })
    additions = load_auxiliary_training()
    for row in additions:
        for alternative in row["alternatives"]:
            extended.append({
                "anchor": row["question"], "positive": alternative,
                "intent_id": row["intent_id"],
            })
    assert len(extended) == 196  # 74*2 + 24*2
    return extended


def summary():
    baseline, *_ = evaluate()
    additions = load_auxiliary_training()
    return {
        "existing_gallery_intents": len(baseline),
        "unchanged_val_intents": sum(r["split"] == "validation" for r in baseline),
        "unchanged_test_intents": sum(r["split"] == "test" for r in baseline),
        "baseline_train_pairs": len(positive_pairs(baseline)),
        "own_train_only_added_intents": len(additions),
        "own_train_only_alternatives": sum(len(r["alternatives"]) for r in additions),
        "augmented_train_positive_pairs": len(augmented_positive_pairs()),
        "domains_added": dict(sorted(Counter(r["domain"] for r in additions).items())),
        "external_dataset_used": False,
        "commercial_training_approved": False,
    }


def main():
    import json as _json
    print("D05_OWNED_AUGMENTATION=" + _json.dumps(summary(), ensure_ascii=True))


if __name__ == "__main__":
    main()
