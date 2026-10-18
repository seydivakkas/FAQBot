"""FAQVec-TR D01 — pinned original file acquisition; explicit CI/user command only."""
import argparse
import json
from pathlib import Path

from scripts.audit_faqvec_d01 import (
    SOURCE_REPO, SOURCE_SHA, SOURCE_FILE,
    SOURCE_BYTES, SOURCE_LFS_SHA256, file_sha256,
)

def download_original(output):
    from huggingface_hub import HfApi, hf_hub_download
    info=HfApi().dataset_info(SOURCE_REPO, revision=SOURCE_SHA)
    if info.sha != SOURCE_SHA:
        raise RuntimeError("Dataset revision mismatch; abort.")
    meta=info.cardData
    license_str=str(meta.get("license", "") if hasattr(meta, "get")
                    else getattr(meta, "license", "")).lower()
    if license_str != "apache-2.0":
        raise RuntimeError("Dataset license claim changed; abort.")
    target=Path(output).resolve()
    target.mkdir(parents=True,exist_ok=True)
    data=Path(hf_hub_download(repo_id=SOURCE_REPO, repo_type="dataset",
                              filename=SOURCE_FILE, revision=SOURCE_SHA,
                              local_dir=str(target)))
    readme=Path(hf_hub_download(repo_id=SOURCE_REPO, repo_type="dataset",
                                filename="README.md", revision=SOURCE_SHA,
                                local_dir=str(target)))
    actual_sha=file_sha256(data)
    if data.stat().st_size != SOURCE_BYTES or actual_sha != SOURCE_LFS_SHA256:
        raise RuntimeError("Original HF LFS artifact hash/size mismatch; abort.")
    meta={
        "repo":SOURCE_REPO, "commit":SOURCE_SHA, "license_claim":license_str,
        "original_file":SOURCE_FILE, "bytes":data.stat().st_size,
        "sha256":actual_sha,
        "readme_sha256":file_sha256(readme),
        "underlying_text_license_review":"HOLD",
        "commercial_training_approved":False,
    }
    (target/"download_provenance.json").write_text(
        json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("D01_DOWNLOAD_VERIFIED="+json.dumps(meta,ensure_ascii=True,separators=(",",":")))
    return data,readme

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output", default="datasets/faqvec_d01_original")
    args=p.parse_args()
    download_original(args.output)

if __name__=="__main__":
    main()
