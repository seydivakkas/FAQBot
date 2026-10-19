"""D05: D04 holdout aynen korunarak gerçek 6 modelin güvenlik/coverage yarışı.

Eşik seçimi yalnız validation'da, test skorları sadece raporlama içindir.
Yeni D05 train-only veri galeriye veya test sorgularına GİRMEZ.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.faqvec_d05_policy import policy_diagnostics, coverage_risk_point
from app.faqvec_v2_metrics import (
    evaluate_matrix, paired_intent_bootstrap_recall_delta
)
from scripts.faqvec_d04_real_benchmark import (
    build_research_suite, compute_scores
)

NAME_MAP = {
    "tfidf": "tfidf",
    "e5-base": "e5-base",
    "faqvec-d04": "faqvec-tr",
    "faqvec-d05": "faqvec-tr",
    "minilm": "minilm",
    "bge-m3": "bge-m3",
}
REQUIRED_MODELS = frozenset(NAME_MAP)
D04_FIXED_TEST_QUERIES = 35
D04_FIXED_VALIDATION_QUERIES = 31


def _check_model(name, path):
    if name not in NAME_MAP:
        raise ValueError("Beklenmeyen model kimliği.")
    if name == "tfidf":
        if path is not None:
            raise ValueError("TF-IDF yerel model klasörü kullanmaz.")
        return
    directory = Path(path).resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Model ağırlığı bulunamadı: {directory}")
    if name.startswith("faqvec-"):
        file = directory / "faqvec_v2_manifest.json"
        if not file.is_file():
            raise ValueError("FAQVec eğitim veri manifesti eksik.")
        meta = json.loads(file.read_text(encoding="utf-8"))
        if meta.get("source_mode") != "ai_reviewed_project_owned_research_only":
            raise ValueError("FAQVec kaynak kökeni uygun değil.")
        if meta.get("research_only") is not True or meta.get("commercial_training_approved") is not False:
            raise ValueError("Ticari onaysız araştırma sözleşmesi eksik.")
        if name == "faqvec-d05" and (
                meta.get("d05_owned_expansion") is not True
                or meta.get("d05_train_auxiliary_intents") != 24
                or meta.get("train_pairs") != 196):
            raise ValueError("D05 modelinin gerçek 196 çiftlik eğitim kaydı eksik.")
        if name == "faqvec-d04" and meta.get("d05_owned_expansion") is True:
            raise ValueError("D05 modeli D04 kontrol modeli yerine kullanılamaz.")


def run_experiment(specs, *, latency_samples=8, batch_size=8):
    ids, gallery, queries = build_research_suite()
    if (len(ids) != 96
            or len(queries["validation"]) != D04_FIXED_VALIDATION_QUERIES
            or len(queries["test"]) != D04_FIXED_TEST_QUERIES):
        raise ValueError("D04 sabitlenmiş galeri/test bölmeleri değiştirildi.")
    val_labels = [x["expected_id"] for x in queries["validation"]]
    test_labels = [x["expected_id"] for x in queries["test"]]
    if sum(x is None for x in val_labels) != 11 or sum(x is None for x in test_labels) != 11:
        raise ValueError("D04 yanıtsızlık bölmeleri değiştirilmiş.")
    names = [name for name, _ in specs]
    if len(names) != len(set(names)):
        raise ValueError("Aynı model iki kere yarıştırılamaz.")
    report = {
        "stage": "D05",
        "measurement_date": datetime.now(timezone.utc).isoformat(),
        "policy": "validation-only-d04-versus-d05-guardrail",
        "data": "original project synthetic AI-reviewed D03; D05 24 train-only intents",
        "source_policy": "OWNED-or-verified-CC0-only",
        "third_party_question_dataset_used": False,
        "human_labels": False,
        "independent_customer_test": False,
        "commercial_release": "HOLD",
        "d04_gallery_unchanged": True,
        "gallery": len(ids),
        "validation_queries": len(val_labels),
        "test_queries": len(test_labels),
        "validation_positive": sum(x is not None for x in val_labels),
        "validation_oos": sum(x is None for x in val_labels),
        "test_positive": sum(x is not None for x in test_labels),
        "test_oos": sum(x is None for x in test_labels),
        "latency_samples": latency_samples,
        "models": [],
        "paired_deltas_top1": {},
    }
    test_matrices = {}
    for name, path in specs:
        _check_model(name, path)
        alias = NAME_MAP[name]
        validation, testing, perf = compute_scores(
            alias, path, gallery, queries,
            latency_samples=latency_samples, batch_size=batch_size
        )
        diagnostics = policy_diagnostics(validation, ids, val_labels)
        d04_cut = diagnostics["d04_penalty_threshold"]
        d05_cut = diagnostics["d05_guardrail"]["threshold"]
        baseline = evaluate_matrix(testing, ids, test_labels, d04_cut)
        policy = evaluate_matrix(testing, ids, test_labels, d05_cut)
        report["models"].append({
            "name": name,
            "model_path": str(Path(path).resolve()) if path else None,
            "measured": True,
            "validation_diagnostics": diagnostics,
            "d04_policy_test": baseline,
            "d05_policy_test": policy,
            "d05_test_coverage_risk": coverage_risk_point(
                testing, ids, test_labels, d05_cut
            ),
            "d05_test_guardrails_observed": (
                policy["wrong_match_rate"] <= 0.10 and
                policy["false_answer_rate"] <= 0.10
            ),
            "performance": perf,
            "decision": "research_only_not_commercial"
        })
        test_matrices[name] = testing
    for challenger in ("faqvec-d04", "faqvec-d05", "bge-m3"):
        if challenger in test_matrices:
            report["paired_deltas_top1"][challenger] = {}
            for baseline in ("e5-base", "faqvec-d04", "bge-m3"):
                if baseline in test_matrices and baseline != challenger:
                    report["paired_deltas_top1"][challenger][baseline] = (
                        paired_intent_bootstrap_recall_delta(
                            test_matrices[baseline], test_matrices[challenger],
                            ids, test_labels
                        )
                    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai-owned-research", action="store_true", required=True)
    parser.add_argument("--model", action="append", default=[],
                        help="Model adı=yerel ağırlık dizini (tfidf otomatik)")
    parser.add_argument("--require-all", action="store_true",
                        help="Gerçek altılı yarış için bütün modeller zorunlu")
    parser.add_argument("--output", default="reports/faqvec_d05_research.json")
    parser.add_argument("--latency-samples", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.latency_samples <= 100 or not 1 <= args.batch_size <= 32:
        parser.error("Ölçüm parametresi uygun aralıkta değil.")
    specs = [("tfidf", None)]
    for flag in args.model:
        if "=" not in flag:
            parser.error("--model adı=yerel/dizin gerekir.")
        name, path = flag.split("=", 1)
        if name not in NAME_MAP or name == "tfidf" or not path:
            parser.error("Model kimliği veya yol hatalı.")
        specs.append((name, path))
    if args.require_all and set(x[0] for x in specs) != REQUIRED_MODELS:
        parser.error("Gerçek altılı yarışın tüm modelleri eksik.")
    os.environ.update({
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "WANDB_DISABLED": "true"
    })
    report = run_experiment(
        specs, latency_samples=args.latency_samples, batch_size=args.batch_size
    )
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("Önceki ölçüm raporunun üzerine yazılmaz.")
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print("D05_RESULTS=" + json.dumps({
        "models": [
            {"name": r["name"],
             "recall_at_1": r["d05_policy_test"]["recall_at_1"],
             "overall_accuracy": r["d05_policy_test"]["overall_accuracy"],
             "positive_abstention_rate": r["d05_policy_test"]["positive_abstention_rate"],
             "wrong_match_rate": r["d05_policy_test"]["wrong_match_rate"],
             "false_answer_rate": r["d05_policy_test"]["false_answer_rate"],
             "guardrail_test_met": r["d05_test_guardrails_observed"]}
            for r in report["models"]
        ],
        "report": str(path), "commercial_release": "HOLD"
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
