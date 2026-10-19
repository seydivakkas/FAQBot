"""FAQVec-TR-V2-D02: iki bağımsız gözlü yerel inceleme, açık hak kapısı.

Özgün D01 JSONL dosyası dışında model/dataset indirmez.
Ham cümleler yalnızca özel yerel inceleme dosyasında tutulur.
Eğitime onaylı triplet üretmez; insan semantiği ve haklar ayrı kapılardır.
"""
import argparse
import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from app.faqvec_v2_data import split_intent
from app.matching import normalize
from scripts.audit_faqvec_d01 import (
    SOURCE_SHA, SOURCE_LFS_SHA256, SOURCE_FILE, file_sha256,
)

BUNDLE_SCHEMA = 1
DECISIONS = {"same", "different", "uncertain"}
SENSITIVE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|https?://|www\.|\b\d{9,}\b", re.I)


def normalized_pair(a, b):
    return tuple(sorted((a, b)))


def digest(payload):
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def collect_graph(path, *, verify_pin=True):
    path = Path(path)
    if verify_pin and file_sha256(path) != SOURCE_LFS_SHA256:
        raise ValueError("D01 JSONL SHA-256 uyuşmuyor.")
    records, display = {}, {}
    with path.open(encoding="utf-8") as stream:
        for line_id, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(row, dict):
                continue
            a, b, label = row.get("sentence1"), row.get("sentence2"), row.get("label")
            if not isinstance(a, str) or not isinstance(b, str):
                continue
            if type(label) is not int or label not in (0, 1):
                continue
            if len(a) > 1000 or len(b) > 1000:
                continue
            na, nb = normalize(a), normalize(b)
            if not na or not nb or na == nb:
                continue
            pair = normalized_pair(na, nb)
            entry = records.setdefault(pair, {"labels": set(), "rows": []})
            entry["labels"].add(label)
            if not entry["rows"]:
                entry["rows"].append(line_id)
            for n, original in ((na, a.strip()), (nb, b.strip())):
                if n not in display or (len(original), original) < (len(display[n]), display[n]):
                    display[n] = original

    parents = {text: text for text in display}
    def find(text):
        while parents[text] != text:
            parents[text] = parents[parents[text]]
            text = parents[text]
        return text
    def union(a, b):
        x, y = find(a), find(b)
        if x != y:
            parents[max(x, y)] = min(x, y)

    for (a, b), item in sorted(records.items()):
        if item["labels"] == {1}:
            union(a, b)
    components = defaultdict(set)
    for phrase in display:
        components[find(phrase)].add(phrase)
    pos = {edge: item for edge, item in records.items() if item["labels"] == {1}}
    neg = {edge: item for edge, item in records.items() if item["labels"] == {0}}
    direct = [edge for edge, item in records.items() if len(item["labels"]) > 1]
    internal = [edge for edge in neg if find(edge[0]) == find(edge[1])]
    big = {root for root, phrases in components.items() if len(phrases) > 25}
    conflict = {find(text) for edge in direct + internal for text in edge}
    quarantine = big | conflict
    safe = {root for root, phr in components.items() if len(phr) >= 2 and root not in quarantine}
    def ident(root):
        return "pair-" + hashlib.sha256("\n".join(sorted(components[root])).encode("utf-8")).hexdigest()[:20]
    ids = {root: ident(root) for root in components}
    return {
        "records": records, "display": display, "find": find,
        "components": components, "pos": pos, "neg": neg,
        "direct": direct, "internal": internal, "large": big,
        "conflicted": conflict, "quarantine": quarantine,
        "safe": safe, "ids": ids,
    }


def lexical_similarity(a, b):
    """Deterministik, ağsız Jaccard; sıralama kanıtı, semantik etiket DEĞİL."""
    def chunks(s):
        t = "^" + s + "$"
        return {t[i:i+3] for i in range(max(0, len(t)-2))}
    aa, bb = chunks(a), chunks(b)
    return len(aa & bb) / len(aa | bb) if aa | bb else 0.0


def generate_bundle(path, *, verify_pin=True, neg_limit=200,
                    positive_limit=60, quarantine_per_component=5):
    if not 1 <= neg_limit <= 10000 or not 1 <= positive_limit <= 1000:
        raise ValueError("İnceleme limitleri geçersiz.")
    graph = collect_graph(path, verify_pin=verify_pin)
    find, ids = graph["find"], graph["ids"]
    sources = []
    for edge, item in graph["pos"].items():
        root = find(edge[0])
        if root in graph["quarantine"]:
            sources.append(("quarantined_positive", edge, item, None, 1.0))
    for edge in graph["direct"]:
        sources.append(("direct_conflict", edge, graph["records"][edge], None, 1.0))
    for edge in graph["internal"]:
        sources.append(("transitive_conflict", edge, graph["records"][edge], None, 1.0))
    by_root = defaultdict(list)
    for kind, edge, item, _, score in sources:
        by_root[find(edge[0])].append((kind, edge, item, score))
    selected = []
    for root in sorted(by_root):
        # Önce çelişkileri, ardından bağlantı kenarlarının sınırlarını incele.
        order = sorted(by_root[root], key=lambda x: (
            0 if x[0] == "direct_conflict" else
            1 if x[0] == "transitive_conflict" else 2,
            x[1],
        ))
        selected.extend(order[:quarantine_per_component])

    controls = sorted(
        ((edge, item) for edge, item in graph["pos"].items()
         if find(edge[0]) in graph["safe"]), key=lambda x: x[0]
    )
    rng = random.Random(42)
    if len(controls) > positive_limit:
        controls = rng.sample(controls, positive_limit)
    selected.extend(("control_positive", edge, item, 0.0) for edge, item in controls)

    negatives = []
    for edge, item in graph["neg"].items():
        a, b = edge
        aroot, broot = find(a), find(b)
        if aroot == broot or aroot not in graph["safe"] or broot not in graph["safe"]:
            continue
        # Cross-split pairs may be reviewed but MUST NOT enter training.
        split_a, split_b = split_intent(ids[aroot]), split_intent(ids[broot])
        score = lexical_similarity(a, b)
        negatives.append((score, edge, item, split_a, split_b))
    negatives.sort(key=lambda x: (-x[0], x[1]))
    selected.extend(
        ("negative_candidate", edge, item, score)
        for score, edge, item, _, _ in negatives[:neg_limit]
    )

    tasks = []
    excluded_sensitive = 0
    for kind, edge, item, score in selected:
        a, b = edge
        texts = [graph["display"][a], graph["display"][b]]
        if any(SENSITIVE.search(text) for text in texts):
            excluded_sensitive += 1
            continue
        ra, rb = find(a), find(b)
        ia, ib = ids[ra], ids[rb]
        sa, sb = split_intent(ia), split_intent(ib)
        identity = hashlib.sha256(
            (SOURCE_SHA + ":" + kind + ":" + a + "\n" + b).encode("utf-8")
        ).hexdigest()[:24]
        tasks.append({
            "task_id": "D02-" + identity,
            "question_a": texts[0], "question_b": texts[1],
            "source_rows": item["rows"],
            "reason": kind, "original_intent_a": ia,
            "original_intent_b": ib, "split_a": sa, "split_b": sb,
            "lexical_candidate_score": round(score, 4),
            "train_negative_eligible_if_approved": (
                kind == "negative_candidate" and sa == sb == "train"
            ),
        })
    tasks.sort(key=lambda task: (task["reason"], task["task_id"]))
    data = {
        "schema": BUNDLE_SCHEMA,
        "source_sha256": file_sha256(path),
        "source_revision": SOURCE_SHA,
        "source_filename": SOURCE_FILE,
        "commercial_training_approved": False,
        "semantic_ground_truth_approved": False,
        "tasks": tasks,
    }
    data["bundle_id"] = digest(data)
    frozen_test = sorted(
        ids[root] for root in graph["safe"] if split_intent(ids[root]) == "test"
    )
    freeze = {
        "source_sha256": data["source_sha256"], "source_revision": SOURCE_SHA,
        "split_contract": "faqvec-v2-split-2026-10",
        "test_candidate_intent_ids": frozen_test,
        "candidate_only": True, "independent_customer_test": False,
        "usable_for_final_acceptance": False,
    }
    freeze["freeze_sha256"] = digest(freeze)
    summary = {
        "source_sha256": data["source_sha256"],
        "unique_quarantine_components": len(graph["quarantine"]),
        "candidate_intents": len(graph["safe"]),
        "frozen_test_candidate_intents": len(frozen_test),
        "review_tasks": len(tasks),
        "review_task_counts": dict(sorted(
            (name, sum(task["reason"] == name for task in tasks))
            for name in {task["reason"] for task in tasks}
        )),
        "negative_candidates_ranked": len(negatives),
        "sensitive_pairs_excluded": excluded_sensitive,
        "human_approved_pairs": 0,
        "human_approved_negative_pairs": 0,
        "rights_clearance": "HOLD",
        "model_training": "BLOCKED",
    }
    return data, freeze, summary


def validate_bundle(bundle):
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("Bilinmeyen D02 paket şeması.")
    base = {key: value for key, value in bundle.items() if key != "bundle_id"}
    if bundle.get("bundle_id") != digest(base):
        raise ValueError("D02 görev paketi değiştirilmiş; bütünlük hatası.")
    ids = [task["task_id"] for task in bundle["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("D02 görev kimlikleri tekrar ediyor.")


def aggregate(bundle, reviews_a, reviews_b):
    validate_bundle(bundle)
    readers = [reviews_a, reviews_b]
    reviewers = [x.get("reviewer_id", "").strip() for x in readers]
    if len(set(reviewers)) != 2 or not all(reviewers):
        raise ValueError("İki FARKLI incelemeci kimliği gerekiyor.")
    checks = []
    tasks = {task["task_id"]:task for task in bundle["tasks"]}
    for review, reviewer in zip(readers, reviewers):
        if review.get("schema") != 1 or review.get("bundle_id") != bundle["bundle_id"]:
            raise ValueError("İnceleme dosyası kaynak görev paketiyle eşleşmiyor.")
        decisions = {}
        for row in review.get("decisions", []):
            key, decision = row.get("task_id"), row.get("decision")
            if key not in tasks or key in decisions or decision not in DECISIONS:
                raise ValueError("Yinelenen/bilinmeyen görev veya hatalı karar.")
            if not isinstance(row.get("note", ""), str):
                raise ValueError("Not bir metin olmalı.")
            decisions[key] = decision
        checks.append(decisions)

    totals = defaultdict(int)
    pending_tasks = []
    research_negatives = []
    for task_id, task in sorted(tasks.items()):
        a, b = checks[0].get(task_id), checks[1].get(task_id)
        if a is None or b is None:
            outcome = "pending"
        elif a == b and a != "uncertain":
            outcome = "dual_agreement_" + a
        elif a == "uncertain" or b == "uncertain":
            outcome = "uncertain"
        else:
            outcome = "disagreement"
        totals[outcome] += 1
        if outcome not in ("dual_agreement_same", "dual_agreement_different"):
            pending_tasks.append({"task_id": task_id, "outcome": outcome})
        if (outcome == "dual_agreement_different"
                and task["reason"] == "negative_candidate"
                and task["train_negative_eligible_if_approved"]):
            research_negatives.append({
                "task_id": task_id, "anchor_intent": task["original_intent_a"],
                "negative_intent": task["original_intent_b"],
                "status": "reviewed_rights_hold",
                "reviewers": reviewers,
            })

    return {
        "schema": 1, "source_sha256": bundle["source_sha256"],
        "bundle_id": bundle["bundle_id"],
        "reviewer_ids": reviewers, "task_count": len(tasks),
        "outcomes": dict(totals),
        "pending_tasks": pending_tasks,
        "research_only_negatives": research_negatives,
        "commercially_approved_negatives": 0,
        "rights_evidence_status": "NOT_INDEPENDENTLY_VERIFIED",
        "human_semantic_review_status": (
            "PARTIAL" if totals["pending"] or totals["disagreement"] or
            totals["uncertain"] else "TWO_REVIEWS_RECORDED"
        ),
        "commercial_training": "HOLD",
        "independent_customer_test": "HOLD",
        "note": "Çift insan onayı hukuki veri kullanım hakkı vermez.",
    }


def write_new(path, obj):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("Var olan veri/karar dosyasının üzerine yazılamaz: " + str(destination))
    destination.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--input", required=True)
    prepare.add_argument("--output-dir", default="reports/faqvec-d02")
    prepare.add_argument("--negative-limit", type=int, default=200)
    prepare.add_argument("--fixture-only", action="store_true")
    assess = sub.add_parser("aggregate")
    assess.add_argument("--bundle", required=True)
    assess.add_argument("--review-a", required=True)
    assess.add_argument("--review-b", required=True)
    assess.add_argument("--output", required=True)
    args = p.parse_args()
    if args.command == "prepare":
        raise SystemExit(
            "D02 üçüncü taraf kaynak işleme hattı kullanıcının telifsiz veri "
            "politikasıyla durduruldu. Yalnız kendi veya doğrulanmış CC0 veriyi kullanın."
        )
        bundle, freeze, summary = generate_bundle(
            args.input, verify_pin=not args.fixture_only,
            neg_limit=args.negative_limit
        )
        folder = Path(args.output_dir)
        write_new(folder / "review_bundle.PRIVATE.json", bundle)
        write_new(folder / "frozen_candidate_test_ids.json", freeze)
        write_new(folder / "summary.json", summary)
        print("D02_RESULT_JSON=" + json.dumps(summary, ensure_ascii=True))
    else:
        load = lambda file: json.loads(Path(file).read_text(encoding="utf-8"))
        report = aggregate(load(args.bundle), load(args.review_a), load(args.review_b))
        write_new(args.output, report)
        print("D02_REVIEW_JSON=" + json.dumps(
            {k:v for k,v in report.items() if k not in ("research_only_negatives","pending_tasks")},
            ensure_ascii=True
        ))


if __name__ == "__main__":
    main()
