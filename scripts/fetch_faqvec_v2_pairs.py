"""Açık kullanıcı çağrısıyla Türkçe paraphrase veri kümesini sabit revizyonla indir.

Bu komut indirilen veri için kullanım hakkı ONAYI üretmez; yalnızca
kaynak repo/revizyon/lisans beyanı için teknik kanıt kaydeder.
Normal FAQBot çalışması, eğitimi ve benchmark internet gerektirmez.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = "dogukanvzr/ml-paraphrase-tr"
EXPECTED_LICENSE = "apache-2.0"


def fetch(repo=REPO, output="datasets/faqvec_raw_paraphrase_tr"):
    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().dataset_info(repo, revision="main")
    revision = info.sha
    if not revision or len(revision) != 40:
        raise RuntimeError("Kaynak dataset için sabit revizyon SHA alınamadı.")
    card = info.cardData
    license_name = str((card or {}).get("license", "")).lower()
    if license_name != EXPECTED_LICENSE:
        raise RuntimeError("Apache-2.0 veri kartı beyanı doğrulanamadı; indirme reddedildi.")
    target = Path(output).resolve()
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("Çıktı klasörü dolu; mevcut verinin üzerine yazılamaz.")
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo, repo_type="dataset", revision=revision,
        local_dir=str(target),
        allow_patterns=["*.json", "*.jsonl", "*.parquet", "README.md", "LICENSE"],
    )
    index = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and ".cache" not in path.parts:
            index.append({
                "path": str(path.relative_to(target)).replace("\\", "/"),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            })
    data_files = [v for v in index if v["path"].lower().endswith(
        (".json", ".jsonl", ".parquet")
    ) and v["path"] != "faqvec_source_candidate.json"]
    if not data_files:
        raise RuntimeError("Desteklenen ham veri dosyası bulunamadı.")
    manifest = {
        "source": repo,
        "revision": revision,
        "declared_license": EXPECTED_LICENSE,
        "license_review_status": "PENDING_INDEPENDENT_PROVENANCE_REVIEW",
        "human_annotation_review": "PENDING",
        "commercial_training_approved": False,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "files": index,
    }
    destination = target / "faqvec_source_candidate.json"
    destination.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Downloaded candidate revision:", revision)
    print("Data files:", [v["path"] for v in data_files])
    print("Commercial data clearance: PENDING")
    print("After rights review prepare records with scripts.prepare_faqvec_v2_pairs")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="datasets/faqvec_raw_paraphrase_tr")
    args = parser.parse_args()
    fetch(output=args.output)


if __name__ == "__main__":
    main()
