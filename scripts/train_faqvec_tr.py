"""FAQVec-TR v0.1 modelini mevcut projeye ait demo sorularından yerelde eğit.

Kullanım:
    python -m scripts.train_faqvec_tr --epochs 30

Haricî model, API veya eğitim veri indirmesi yapmaz.
Gerçek müşteriye ait soru metinlerini otomatik olarak eğitime eklemez.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.database import DATA_PATH, V13_DATA_PATH
from app.faqvec_tr import DEFAULT_OWN_DIR, save_model, train_groups


def _source():
    records = []
    for path in (DATA_PATH, V13_DATA_PATH):
        content = json.loads(path.read_text(encoding="utf-8"))
        records.extend(content)
    groups = []
    for record in records:
        group = [record["question"], *record.get("alternative_questions", [])]
        if len(set(group)) >= 2:
            groups.append(group)
    return groups


def _recall(encoder, groups):
    """Bekletilmiş niyetlerde alternatif sorunun doğru ana soruyu bulma oranı."""
    if not groups:
        return None, None, 0
    gallery = [g[0] for g in groups]
    query = [phrase for g in groups for phrase in g[1:]]
    goals = [i for i, g in enumerate(groups) for _ in g[1:]]
    v_gallery = encoder.encode(gallery)
    v_query = encoder.encode(query)
    pred = (v_query @ v_gallery.T).argmax(axis=1)
    actual = float(np.mean(pred == np.asarray(goals)))
    baseline = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))
    v_b = baseline.fit_transform(gallery)
    q_b = baseline.transform(query)
    base_pred = cosine_similarity(q_b, v_b).argmax(axis=1)
    baseline_result = float(np.mean(base_pred == np.asarray(goals)))
    return round(actual, 4), round(baseline_result, 4), len(query)


def main():
    parser = argparse.ArgumentParser(description="FAQVec-TR — yerel sıfırdan eğitim")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=str(DEFAULT_OWN_DIR))
    args = parser.parse_args()
    groups = _source()
    if len(groups) < 10:
        raise SystemExit("Eğitim için yeterli SSS niyeti yok.")
    rng = np.random.default_rng(args.seed)
    shuffled = rng.permutation(len(groups)).tolist()
    held_out = max(2, int(round(len(groups) * 0.2)))
    val = [groups[i] for i in shuffled[:held_out]]
    train = [groups[i] for i in shuffled[held_out:]]
    model_eval, _ = train_groups(train, epochs=args.epochs, seed=args.seed)
    recall, baseline, count = _recall(model_eval, val)
    # İndüktif değerlendirmede tutulan niyetler son üretim modeline dahil edilir.
    # Bu nedenle rapor yalnızca ayrı holdout modeliyle hesaplanan metriği belirtir.
    deployed, stats = train_groups(groups, epochs=args.epochs, seed=args.seed)
    source_hash = hashlib.sha256(
        json.dumps(groups, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = save_model(deployed, args.output, {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_source": "bundled_demo_faqs_no_third_party_weights",
        "training_source_sha256": source_hash,
        "data_rights": "REVIEW_REQUIRED_BEFORE_COMMERCIAL_DISTRIBUTION",
        "train_intents": len(groups),
        "train_phrases": sum(map(len, groups)),
        "seed": args.seed,
        **stats,
        "validation": {
            "strategy": "held_out_intents_20pct_before_final_retraining",
            "holdout_intents": len(val),
            "holdout_queries": count,
            "faqvec_recall_at_1": recall,
            "char_tfidf_recall_at_1": baseline,
            "independent_real_customer_test": False,
        },
    })
    print("FAQVec-TR model saved:", args.output)
    print("Dimensions:", manifest["dimensions"], "Train intents:", manifest["train_intents"])
    print("Holdout Recall@1:", recall, "TF-IDF baseline:", baseline)
    print("Commercial acceptance:", manifest["commercial_acceptance"],
          "(data rights and independent model performance review required)")


if __name__ == "__main__":
    main()
