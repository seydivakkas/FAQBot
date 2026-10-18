"""Türkçe etiketli cümle çiftlerinden sızıntı kontrollü SSS niyetleri hazırla.

Ham veri önce insan tarafından köken/lisans açısından incelenmelidir.
Bu betik HİÇBİR veriye ticari kullanım onayı vermez ve model eğitmez.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.faqvec_v2_data import split_intent, validate_intents
from app.matching import normalize


class PairDataError(ValueError):
    pass


def read_pairs(path, *, limit=150000):
    """JSON listesi, JSONL veya Parquet; Parquet sadece opt-in pyarrow ile."""
    file = Path(path)
    if file.suffix == ".jsonl":
        with file.open(encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= limit:
                    raise PairDataError("Satır limiti aşıldı.")
                if line.strip():
                    yield json.loads(line)
    elif file.suffix == ".json":
        rows = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("data", rows.get("train"))
        if not isinstance(rows, list) or len(rows) > limit:
            raise PairDataError("JSON listesi bulunamadı veya limit aşıldı.")
        yield from rows
    elif file.suffix == ".parquet":
        import pyarrow.parquet as pq
        reader = pq.ParquetFile(file)
        seen = 0
        for group in reader.iter_batches(batch_size=1024):
            for row in group.to_pylist():
                seen += 1
                if seen > limit:
                    raise PairDataError("Satır limiti aşıldı.")
                yield row
    else:
        raise PairDataError("Yalnızca JSON, JSONL veya Parquet desteklenir.")


def _text(s):
    if not isinstance(s, str):
        return ""
    return " ".join(s.strip().split())


def _key(a, b):
    return tuple(sorted((a, b)))


def prepare_pairs(rows, *, seed="faqvec-v2-split-2026-10",
                  max_component_size=25, max_phrases=50):
    """Pozitif çiftlerin bağlantılı bileşenlerini aynı split'te tut.

    Negatifler yalnızca denetlenecek aday havuzudur; rastgele olumsuzları
    "hard negative" veya "out-of-scope" kabul etmeyiz.
    """
    parent = {}
    originals = {}
    positives, negatives = set(), set()
    stats = Counter()
    for index, row in enumerate(rows, 1):
        a = _text(row.get("sentence1"))
        b = _text(row.get("sentence2"))
        na, nb = normalize(a), normalize(b)
        label = row.get("label")
        if not na or not nb or na == nb or label not in (0, 1):
            stats["invalid_or_identical"] += 1
            continue
        if len(a) > 1000 or len(b) > 1000:
            stats["overlong"] += 1
            continue
        for n, t in ((na, a), (nb, b)):
            parent.setdefault(n, n)
            if n not in originals or (len(t), t) < (len(originals[n]), originals[n]):
                originals[n] = t
        edge = _key(na, nb)
        if label == 1:
            positives.add(edge)
        else:
            negatives.add(edge)

    contradictions = positives & negatives
    if contradictions:
        # Karşıt etiketli çiftlerden pozitif küme kurmak sızıntı ve yanlış
        # semantik öğretebilir. İnceleme bitmeden fail-closed.
        raise PairDataError(f"{len(contradictions)} çiftte olumlu/olumsuz etiket çelişkisi.")

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for a, b in sorted(positives):
        union(a, b)
    clusters = defaultdict(set)
    for phrase in parent:
        clusters[root(phrase)].add(phrase)

    # Büyük bir transitif bileşen, muhtemel çok anlamlı bağlantı olabilir.
    suspicious = {key for key, group in clusters.items()
                  if len(group) > max_component_size}
    crossed = [(a, b) for a, b in negatives if root(a) == root(b)]
    stats["negative_inside_positive_cluster"] = len(crossed)
    if crossed:
        raise PairDataError(
            f"{len(crossed)} negatif çift pozitif eşanlamlı bileşen içine düştü; insan incelemesi gerekli."
        )
    output = []
    component_map = {}
    for key, nodes in sorted(clusters.items()):
        if len(nodes) < 2:
            continue
        if key in suspicious:
            stats["quarantined_large_clusters"] += 1
            continue
        selected = sorted(nodes, key=lambda q: (len(q), q))[:max_phrases]
        signature = hashlib.sha256(
            "\n".join(sorted(nodes)).encode("utf-8")
        ).hexdigest()[:20]
        ident = "pair-" + signature
        component_map[key] = ident
        output.append({
            "intent_id": ident,
            "split": split_intent(ident, seed),
            "question": originals[selected[0]],
            "alternatives": [originals[n] for n in selected[1:]],
            "source_id": "turkish-paraphrase-candidate",
            "rights_verified": False,
        })
    if not output:
        raise PairDataError("Hiç uygun pozitif soru grubu üretilemedi.")
    # normalized cümleleri paylaşan gruplar union ile bağlandığından farklı
    # train/validation/test split'leri arasında cümle kaçağı yoktur.
    summary = validate_intents(output)
    stats.update({"positive_pairs": len(positives),
                  "random_negative_pairs": len(negatives),
                  "accepted_intents": len(output),
                  "source_phrases": len(parent)})
    candidates = []
    for a, b in sorted(negatives):
        ka, kb = root(a), root(b)
        if ka in component_map and kb in component_map:
            candidates.append({
                "anchor_intent": component_map[ka],
                "negative_intent": component_map[kb],
                "anchor": originals[a],
                "candidate_negative": originals[b],
                "status": "needs_human_review",
                "reviewed_by": None,
                "warning": "Rastgele olumsuz çift; zor negatif olduğu doğrulanmadı.",
            })
    return output, candidates, {"statistics": dict(stats), "split_intents": summary}


def save_candidate_package(records, candidates, summary, *, source_file, output_dir,
                           source_repo, revision, card_path=None):
    folder = Path(output_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "turkish_pairs_candidate.jsonl"
    neg = folder / "negative_candidates_unreviewed.jsonl"
    output.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n"
                              for x in records), encoding="utf-8")
    neg.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n"
                           for x in candidates), encoding="utf-8")
    source_path = Path(source_file)
    evidence_name = None
    if card_path:
        # Kaynak kartının birebir kopyasını aday paketiyle birlikte sakla.
        evidence_name = "SOURCE_CARD_EVIDENCE.md"
        (folder / evidence_name).write_bytes(Path(card_path).read_bytes())
    card_sha = (hashlib.sha256((folder / evidence_name).read_bytes()).hexdigest()
                if evidence_name else None)
    manifest = {
        "schema_version": 1,
        "sources": [{
            "id": "turkish-paraphrase-candidate",
            "origin_url": f"https://huggingface.co/datasets/{source_repo}/tree/{revision}",
            "license_spdx": "Apache-2.0",
            "license_claim_source": "dataset_card_NOT_INDEPENDENTLY_VERIFIED",
            "rights_review_status": "PENDING",
            "reviewed_by": None,
            "evidence_sha256": card_sha,
            "evidence_file": evidence_name,
            "commercial_training_approved": False,
        }],
        "files": [{
            "path": output.name,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "source_file_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        }],
        "source_repo": source_repo,
        "source_revision": revision,
        "data_quality": summary,
        "hard_negatives_status": "NEEDS_HUMAN_REVIEW",
        "commercial_acceptance": "HOLD",
    }
    path = folder / "manifest.CANDIDATE.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--source-repo", default="dogukanvzr/ml-paraphrase-tr")
    parser.add_argument("--revision", required=True, help="Kaynağın commit SHA'sı.")
    parser.add_argument("--card-path", help="Kaynak README.md dosyası; SHA kanıtı")
    parser.add_argument("--output", default="reports/faqvec_v2_pairs")
    args = parser.parse_args()
    rows, negatives, report = prepare_pairs(read_pairs(args.source_file))
    path = save_candidate_package(
        rows, negatives, report, source_file=args.source_file,
        output_dir=args.output, source_repo=args.source_repo,
        revision=args.revision, card_path=args.card_path
    )
    print("Candidate dataset manifest:", path)
    print("Reviewed/commercially approved: NO")
    print("Summary:", json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
