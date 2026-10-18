"""FAQVec-TR v0.2: adil, ağsız TF-IDF/E5/BGE/MiniLM/FAQVec karşılaştırması.

Tüm algoritmalar aynı galeri ve insan etiketli test sorgularını kullanır.
Eşik sadece validation setinde, onaylı cevap-yok örnekleriyle kalibre edilir.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.faqvec_v2_data import (
    _read_jsonl, load_approved_sources, load_bundled_demo, validate_intents,
)
from app.faqvec_v2_metrics import (evaluate_matrix, thresholds_on_validation,
                                     paired_intent_bootstrap_recall_delta)
from app.matching import normalize


def build_suite(records, negative_file=None):
    """Galeri tüm ihtiyaçlar; test sorgusu niyet düzeyinde ayrılmış."""
    validate_intents(records)
    by_intent = {}
    for row in records:
        if row["intent_id"] in by_intent:
            raise ValueError("Benchmark'ta her niyet için yalnızca bir kanonik kayıt olmalı.")
        by_intent[row["intent_id"]] = row
    gallery = sorted(by_intent)
    texts = [by_intent[key]["question"] for key in gallery]
    queries = {"validation": [], "test": []}
    for intent, row in sorted(by_intent.items()):
        if row["split"] in queries:
            for query in row.get("alternatives", []):
                queries[row["split"]].append({"query": query, "expected_id": intent,
                                               "source": "faq_intent"})
    if negative_file:
        normalized_gallery = {normalize(text) for text in texts}
        seen = set()
        for entry in _read_jsonl(negative_file):
            if entry.get("review_status") != "approved" or not entry.get("reviewed_by"):
                continue
            if entry.get("split") not in queries or entry.get("expected_id", "bad") is not None:
                raise ValueError("Onaylı no-answer kaydında split/expected_id geçersiz.")
            text = entry.get("query", "")
            key = normalize(text)
            if not key or key in normalized_gallery or key in seen:
                raise ValueError("No-answer test sorgusu galeriyle veya başka sorguyla çakışıyor.")
            seen.add(key)
            queries[entry["split"]].append({"query": text, "expected_id": None,
                                             "source": "human_approved_out_of_scope"})
    return gallery, texts, queries


def tfidf_scores(gallery, queries):
    model = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                            lowercase=False, sublinear_tf=True)
    gallery_vectors = model.fit_transform([normalize(x) for x in gallery])
    return cosine_similarity(
        model.transform([normalize(q) for q in queries]), gallery_vectors
    )


def embedding_scores(model_dir, gallery, queries, e5=False):
    # No internet and no remote model identifier: paths only.
    directory = Path(model_dir).resolve()
    if not directory.is_dir():
        raise ValueError("Embedding klasörü yerel diskte bulunamadı.")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(directory),
                                local_files_only=True, trust_remote_code=False)
    prefix = "query: " if e5 else ""
    corpus = [prefix + text for text in gallery]
    inp = [prefix + text for text in queries]
    gallery_vectors = np.asarray(model.encode(
        corpus, normalize_embeddings=True, convert_to_numpy=True,
        show_progress_bar=False), dtype=np.float32)
    query_vectors = np.asarray(model.encode(
        inp, normalize_embeddings=True, convert_to_numpy=True,
        show_progress_bar=False), dtype=np.float32)
    return query_vectors @ gallery_vectors.T


def benchmark(records, specs, negative_file=None):
    gallery_ids, gallery_text, queries = build_suite(records, negative_file)
    val = queries["validation"]
    test = queries["test"]
    if not val or not test:
        raise ValueError("Validation ve test kümeleri dolu olmalı.")
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gallery_size": len(gallery_ids),
        "validation_queries": len(val), "test_queries": len(test),
        "verified_negative_validation": sum(q["expected_id"] is None for q in val),
        "verified_negative_test": sum(q["expected_id"] is None for q in test),
        "models": [],
        "note": "Demo SSS testleri bağımsız gerçek müşteri ölçümü değildir.",
    }
    test_score_matrices = {}
    for name, modelpath, e5 in specs:
        def calc(q):
            texts = [i["query"] for i in q]
            return tfidf_scores(gallery_text, texts) if name == "tfidf" else \
                embedding_scores(modelpath, gallery_text, texts, e5=e5)
        valid_matrix, test_matrix = calc(val), calc(test)
        test_score_matrices[name] = test_matrix
        valid_labels = [q["expected_id"] for q in val]
        test_labels = [q["expected_id"] for q in test]
        if any(label is None for label in valid_labels):
            threshold = thresholds_on_validation(valid_matrix, gallery_ids, valid_labels)
            calibrated = True
        else:
            # Önceden sabitlenmemiş ve doğrulanmamış bir eşik üretmiyoruz.
            threshold, calibrated = 0.0, False
        report = evaluate_matrix(test_matrix, gallery_ids, test_labels, threshold)
        result["models"].append({
            "name": name, "local_path": str(Path(modelpath).resolve()) if modelpath else None,
            "e5_query_prefix": bool(e5), "validation_calibrated": calibrated,
            "diagnostic_only": not calibrated,
            "test": report,
        })
    # İstatistik karşılaştırması yalnızca eşleştirilmiş AYNI test sorgularında.
    if "tfidf" in test_score_matrices:
        baseline = test_score_matrices["tfidf"]
        labels = [item["expected_id"] for item in test]
        for entry in result["models"]:
            if entry["name"] != "tfidf":
                entry["paired_vs_tfidf"] = paired_intent_bootstrap_recall_delta(
                    baseline, test_score_matrices[entry["name"]], gallery_ids, labels
                )
    return result


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true")
    source.add_argument("--manifest")
    parser.add_argument("--negative-file",
                        help="İnsan onaylı no-answer örnekleri JSONL")
    parser.add_argument("--model", action="append", default=[],
                        help="isim=/mutlak/yerel/model/yolu; e5-base, faqvec-v2, bge-m3, minilm")
    parser.add_argument("--output", default="reports/faqvec_v2_benchmark.json")
    args = parser.parse_args()
    rows = load_bundled_demo() if args.demo else load_approved_sources(args.manifest)[0]
    models = [("tfidf", None, False)]
    for option in args.model:
        if "=" not in option:
            parser.error("--model için isim=yol biçimi gerekli.")
        name, path = option.split("=", 1)
        if name not in ("e5-base", "faqvec-v2", "bge-m3", "minilm"):
            parser.error("Model adı e5-base, faqvec-v2, bge-m3 veya minilm olmalı.")
        models.append((name, path, name in ("e5-base", "faqvec-v2")))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    report = benchmark(rows, models, args.negative_file)
    report["source_type"] = "demo_not_independent" if args.demo else "user_reviewed_manifest"
    report["commercial_acceptance"] = "HOLD"
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(json.dumps({
        "report": str(target), "gallery": report["gallery_size"],
        "models": [{x["name"]: x["test"]["recall_at_1"]} for x in report["models"]],
        "commercial_acceptance": "HOLD"
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
