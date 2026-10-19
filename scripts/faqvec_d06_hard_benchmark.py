"""FAQVec D06: önceden mühürlenmiş 72 yeni Türkçe soru üzerinde tek yönlü test.

Eşik+marj yalnız D04 validation'dan seçilir; D06 etiketlerine yalnız SON
değerlendirmede bakılır. D06 sonucu eğitim model seçimine geri beslenmez.
"""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.faqvec_d05_policy import choose_guardrail_threshold
from app.faqvec_d06_margin_gate import gate_measure, calibrate_validation_margin
from app.faqvec_v2_metrics import paired_intent_bootstrap_recall_delta
from scripts.faqvec_d04_real_benchmark import build_research_suite, compute_scores
from scripts.faqvec_d05_real_benchmark import NAME_MAP, REQUIRED_MODELS, _check_model
from scripts.faqvec_d06_frozen_challenge import (
    challenge_queries, summary, FROZEN_GIT_BLOB,
)

POLICY_SPEC = "D06; calibration only previous D04 validation, challenge never fitted"
REQUIRED_CHALLENGE = 72


def _by_domain(matrix, gallery_ids, rows, threshold, margin):
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[row["domain"]].append(i)
    out = {}
    for domain, idx in sorted(groups.items()):
        labels = [rows[i]["expected_id"] for i in idx]
        values = gate_measure(matrix[idx], gallery_ids, labels,
                              threshold=threshold, margin=margin)
        if values["positive"] != 4 or values["oos"] != 2:
            raise ValueError("D06 alan sayısı değişmiş.")
        out[domain] = {
            "correct_positive": values["correct_positive_count"],
            "wrong_positive": values["wrong_match_count"],
            "positive_abstention": values["positive_abstention_count"],
            "false_oos_answers": values["false_answer_count"],
        }
    return out


def _top1_recalls(matrix, gallery_ids, rows):
    positives = [(i, row) for i, row in enumerate(rows)
                 if row["expected_id"] is not None]
    order = np.argmax(matrix, axis=1)
    ok = sum(
        gallery_ids[order[i]] == row["expected_id"]
        for i, row in positives
    )
    return {
        "correct_top1": int(ok), "total_positives": len(positives),
        "recall_at_1": round(ok / len(positives), 4)
    }


def evaluate_frozen_models(specs, *, latency_samples=8, batch_size=8):
    ids, gallery, old_queries = build_research_suite()
    hard_test = challenge_queries()
    if len(ids) != 96 or len(old_queries["validation"]) != 31 or len(hard_test) != REQUIRED_CHALLENGE:
        raise ValueError("D04 galerisi, kilitli validation veya D06 test değiştirildi.")
    if sum(x["expected_id"] is not None for x in hard_test) != 48:
        raise ValueError("D06 pozitif/OOS test sayısı değiştirildi.")
    old_validation = old_queries["validation"]
    calibration_labels = [q["expected_id"] for q in old_validation]
    hard_labels = [q["expected_id"] for q in hard_test]
    names = [name for name, _ in specs]
    if len(names) != len(set(names)):
        raise ValueError("Model yinelendi.")
    report = {
        "stage": "D06", "created_utc": datetime.now(timezone.utc).isoformat(),
        "test_provenance":"project-authored synthetic AI labels; NOT independently sampled customers",
        "source_git_blob": FROZEN_GIT_BLOB,
        "frozen_challenge": summary(),
        "gallery_count": len(ids), "fixed_calibration_count": len(old_validation),
        "positive_new_questions": 48, "near_miss_oos_new_questions": 24,
        "threshold_selection_source": "D04 validation only",
        "new_test_used_in_training_or_calibration": False,
        "no_external_question_dataset_used": True,
        "independent_customer_test": False,
        "research_only": True, "commercial_acceptance": "HOLD",
        "models": [], "paired_top1_delta": {},
    }
    matrices = {}
    for name, folder in specs:
        _check_model(name, folder)
        model_kind = NAME_MAP[name]
        validation_matrix, test_matrix, perf = compute_scores(
            model_kind, folder, gallery,
            {"validation": old_validation, "test": hard_test},
            latency_samples=latency_samples,
            batch_size=batch_size,
        )
        cutoff = choose_guardrail_threshold(validation_matrix, ids, calibration_labels)
        dual = calibrate_validation_margin(validation_matrix, ids, calibration_labels)
        threshold, margin = dual["selected_threshold"], dual["selected_margin"]
        single_test = gate_measure(test_matrix, ids, hard_labels,
                                   threshold=cutoff["threshold"], margin=0)
        dual_test = gate_measure(test_matrix, ids, hard_labels,
                                 threshold=threshold, margin=margin)
        report["models"].append({
            "name": name,
            "actual_model_measured": name != "tfidf",
            "validation_gate": dual,
            "single_gate_test": single_test,
            "dual_gate_test": dual_test,
            "top1": _top1_recalls(test_matrix, ids, hard_test),
            "dual_gate_per_domain": _by_domain(
                test_matrix, ids, hard_test, threshold, margin
            ),
            "new_test_guardrail_observed": (
                dual_test["wrong_match_rate"] <= 0.10
                and dual_test["false_answer_rate"] <= 0.10
            ),
            "performance": perf,
            "commercial_acceptance": "HOLD",
        })
        matrices[name] = test_matrix
    for challenger in ("faqvec-d05", "bge-m3"):
        if challenger in matrices:
            report["paired_top1_delta"][challenger] = {}
            for control in ("faqvec-d04", "e5-base", "bge-m3", "faqvec-d05"):
                if control in matrices and control != challenger:
                    report["paired_top1_delta"][challenger][control] = (
                        paired_intent_bootstrap_recall_delta(
                            matrices[control],matrices[challenger],ids,hard_labels
                        )
                    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai-owned-research", action="store_true", required=True)
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--require-all", action="store_true")
    parser.add_argument("--output", default="reports/d06_frozen_challenge.json")
    parser.add_argument("--latency-samples", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.latency_samples <= 100 or not 1 <= args.batch_size <= 32:
        parser.error("Ölçüm batch ve tekrarı sınır dışında.")
    specs = [("tfidf", None)]
    for raw in args.model:
        if "=" not in raw:
            parser.error("--model etiket=yerel/model/dizini gerekir.")
        name, folder = raw.split("=", 1)
        if name not in NAME_MAP or name == "tfidf" or not folder:
            parser.error("Model kimliği/yolu hatalı.")
        specs.append((name, folder))
    if args.require_all and set(x[0] for x in specs) != REQUIRED_MODELS:
        parser.error("D06 tam altılı yarış için altı modelin tümü gerekli.")
    os.environ.update({
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "WANDB_DISABLED": "true",
    })
    result = evaluate_frozen_models(
        specs, latency_samples=args.latency_samples,
        batch_size=args.batch_size
    )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("D06 kilitli test raporunun üzerine yazılmaz.")
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("D06_FROZEN_HARD_TEST_RESULTS=" + json.dumps({
        "source_hash":FROZEN_GIT_BLOB,"test_cases":72,
        "models":[{
            "name":x["name"],
            "top1":x["top1"]["recall_at_1"],
            "single_correct":x["single_gate_test"]["overall_correct_count"],
            "dual_correct":x["dual_gate_test"]["overall_correct_count"],
            "dual_wrong":x["dual_gate_test"]["wrong_match_count"],
            "dual_false_oos":x["dual_gate_test"]["false_answer_count"],
            "dual_reject_positive":x["dual_gate_test"]["positive_abstention_count"],
            "safe_on_hard_test":x["new_test_guardrail_observed"],
        } for x in result["models"]],
        "independent_customer_test":False,
        "commercial_acceptance":"HOLD"
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
