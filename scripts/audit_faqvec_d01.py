"""Pinned data integrity and candidate-quality audit. No training or commercial approvals."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from app.faqvec_v2_data import split_intent
from app.matching import normalize

SOURCE_REPO = "dogukanvzr/ml-paraphrase-tr"
SOURCE_SHA = "b9d5707470340db13d788a338e7f7897c5e29932"
SOURCE_FILE = "ml_paraphrase_60k_labeled.jsonl"
SOURCE_BYTES = 16459390
SOURCE_LFS_SHA256 = "2c5bace5f34bbc9bc79084ddf57bc5a298310eaa2614beb9f7862a16b674e39d"

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def audit(path, *, verify_pin=True, source_card=None, max_component_size=25):
    path = Path(path)
    digest = file_sha256(path)
    size = path.stat().st_size
    if verify_pin and (digest != SOURCE_LFS_SHA256 or size != SOURCE_BYTES):
        raise ValueError("Özgün kaynak SHA-256 veya boyutu uyuşmuyor; kabul durduruldu.")
    counts = Counter()
    edges = {}
    phrases = set()
    with path.open(encoding="utf-8") as src:
        for line in src:
            counts["physical_lines"] += 1
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                counts["invalid_json"] += 1
                continue
            if not isinstance(row, dict):
                counts["invalid_schema"] += 1
                continue
            a, b, label = row.get("sentence1"), row.get("sentence2"), row.get("label")
            if not isinstance(a, str) or not isinstance(b, str) or type(label) is not int or label not in (0, 1):
                counts["invalid_schema"] += 1
                continue
            if len(a) > 1000 or len(b) > 1000:
                counts["overlong"] += 1
                continue
            a, b = normalize(a), normalize(b)
            if not a or not b:
                counts["empty_after_normalization"] += 1
                continue
            if a == b:
                counts["same_normalized_phrase"] += 1
                continue
            counts["valid_rows"] += 1
            counts["label_" + str(label) + "_rows"] += 1
            key = (a, b) if a < b else (b, a)
            if key in edges:
                if label in edges[key]:
                    counts["repeated_same_label_rows"] += 1
                else:
                    counts["opposing_label_rows"] += 1
            edges.setdefault(key, set()).add(label)
            phrases.update(key)
    conflicting = {key for key, values in edges.items() if len(values) > 1}
    positive = [key for key, values in edges.items() if values == {1}]
    negative = [key for key, values in edges.items() if values == {0}]
    parents = {key:key for key in phrases}
    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x
    def join(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parents[max(ra, rb)] = min(ra, rb)
    for a,b in positive:
        join(a,b)
    groups = defaultdict(set)
    for phrase in phrases:
        groups[find(phrase)].add(phrase)
    large_groups = {root for root, group in groups.items() if len(group) > max_component_size}
    transitive = [(a,b) for a,b in negative if find(a) == find(b)]
    contradictory_groups = {find(a) for a,b in transitive}
    contradictory_groups.update(find(v) for edge in conflicting for v in edge)
    quarantined = large_groups | contradictory_groups
    safe_groups = {root for root, group in groups.items()
                   if len(group) >= 2 and root not in quarantined}
    approved_negative_candidates = sum(
        find(a) in safe_groups and find(b) in safe_groups and find(a) != find(b)
        for a,b in negative)
    splits = Counter()
    for group in safe_groups:
        identity = "pair-" + hashlib.sha256(
            "\n".join(sorted(groups[group])).encode("utf-8")).hexdigest()[:20]
        splits[split_intent(identity)] += 1
    stats = {
        **{key:int(val) for key,val in sorted(counts.items())},
        "unique_pairs":len(edges),
        "unique_opposing_label_pairs":len(conflicting),
        "unique_positive_pairs_without_direct_conflict":len(positive),
        "unique_negative_pairs_without_direct_conflict":len(negative),
        "distinct_normalized_phrases":len(phrases),
        "positive_components":sum(len(g)>=2 for g in groups.values()),
        "quarantined_large_components":len(large_groups),
        "quarantined_label_conflict_components":len(contradictory_groups),
        "quarantined_components_total":len(quarantined),
        "candidate_intents_needing_human_review":len(safe_groups),
        "candidate_positive_pairs_needing_human_review":sum(find(a) in safe_groups for a,b in positive),
        "quarantined_positive_pairs":sum(find(a) not in safe_groups for a,b in positive),
        "negative_inside_positive_component":len(transitive),
        "negative_pairs_for_human_review":approved_negative_candidates,
        "negative_pairs_excluded_from_review":len(negative)-approved_negative_candidates,
        "commercially_approved_positive_pairs":0,
        "human_approved_hard_negatives":0,
    }
    result = {
        "audit_id":"FAQVec-TR-V2-D01",
        "audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_repo":SOURCE_REPO, "source_revision":SOURCE_SHA,
        "source_filename":SOURCE_FILE, "source_bytes":size,
        "source_sha256":digest,
        "source_card_sha256":file_sha256(source_card) if source_card else None,
        "expected_sha256":SOURCE_LFS_SHA256,
        "declared_license":"Apache-2.0",
        "independently_verified_underlying_text_rights":False,
        "metrics":stats,
        "split_candidate_intents":{k:int(splits[k]) for k in ("train","validation","test")},
        "acceptance":{
            "file_integrity":"PASS" if verify_pin else "FIXTURE_ONLY",
            "semantic_labels":"HOLD",
            "underlying_data_rights":"HOLD",
            "commercial_training":"HOLD",
            "model_performance":"HOLD",
        },
        "note":"Aday sayıları insan tarafından doğrulanmış eğitim verisi değildir.",
    }
    return result

def markdown(result):
    lines = [
        "# FAQVec-TR-V2-D01 — Doğrulanmış özgün dosya denetimi",
        "",
        "Kaynak revizyonu: " + result["source_revision"],
        "Özgün JSONL SHA256: " + result["source_sha256"],
        "Özgün JSONL bayt sayısı: " + str(result["source_bytes"]),
        "Kaynak kartı SHA256: " + str(result["source_card_sha256"]),
        "",
        "| Otomatik sayım | Adet |",
        "| --- | ---: |",
    ]
    lines.extend("| " + k + " | " + str(v) + " |" for k,v in result["metrics"].items())
    lines += ["", "## Aday niyet bölmeleri", ""]
    lines.extend("- " + k + ": " + str(v) for k,v in result["split_candidate_intents"].items())
    lines += ["", "**Veri hakları HOLD. Etiket doğruluğu HOLD. Gerçek model kabulü HOLD.**",
              "Aday niyetler otomatik bağlantılı bileşen yöntemiyle sayılmıştır; onaylanmamıştır."]
    return "\n".join(lines) + "\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--source-card")
    p.add_argument("--output-dir",default="reports/faqvec-d01")
    p.add_argument("--fixture-only",action="store_true",
                   help="Only for local synthetic tests; never evidence for source acceptance")
    a = p.parse_args()
    result = audit(a.input, verify_pin=not a.fixture_only, source_card=a.source_card)
    path = Path(a.output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path/"audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2), encoding="utf-8")
    (path/"audit.md").write_text(markdown(result), encoding="utf-8")
    print("D01_RESULT_JSON=" + json.dumps(result,ensure_ascii=True,separators=(",",":")))

if __name__ == "__main__":
    main()
