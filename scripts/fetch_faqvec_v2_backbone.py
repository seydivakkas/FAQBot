"""Açık kullanıcı komutuyla MIT lisanslı E5 ağırlıklarını bir kez indirir."""
import argparse
import json
from pathlib import Path

REPO = "intfloat/multilingual-e5-base"
LICENSE = "MIT"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="models/e5-base-original")
    parser.add_argument("--revision", default="main", help="Mümkünse sabit 40 karakter commit.")
    args = parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download
    api = HfApi()
    info = api.model_info(REPO, revision=args.revision)
    if info.cardData is None or info.cardData.get("license", "").lower() != "mit":
        raise RuntimeError("Model lisansı MIT olarak doğrulanamadı; indirme durduruldu.")
    directory = Path(args.output).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=REPO, revision=info.sha, local_dir=str(directory),
                      allow_patterns=["*.json", "*.txt", "*.safetensors", "*.md", "*.model", "LICENSE"])
    (directory / "faqvec_backbone_origin.json").write_text(
        json.dumps({
            "repo": REPO, "revision": info.sha, "declared_license": LICENSE,
            "source_url": f"https://huggingface.co/{REPO}/tree/{info.sha}",
            "commercial_review": "REQUIRES_NOTICE_AND_DEPENDENCY_AUDIT",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Model downloaded with pinned revision:", info.sha)
    print("Local directory:", directory)


if __name__ == "__main__":
    main()
