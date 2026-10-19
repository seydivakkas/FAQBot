"""FAQVec D04: yalnız açık lisanslı MODEL AĞIRLIKLARINI bilinçli indirme.

Üçüncü taraf SORU/KORPUS/veri seti indirmez. Kullanıcının açık
--confirm-download tercihi gerekir. İndirilen model daha sonra tamamen
çevrimdışı yüklenir. Ticari yayın onayı üretmez.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MODELS = {
    "e5-base": ("intfloat/multilingual-e5-base","MIT","models/e5-base-original"),
    "minilm": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
               "Apache-2.0","models/minilm-original"),
    "bge-m3": ("BAAI/bge-m3","MIT","models/bge-m3-original"),
}
ALLOWED = [
    "*.json", "**/*.json", "*.safetensors", "**/*.safetensors",
    "*.txt", "**/*.txt", "*.model", "**/*.model",
    "*.bpe", "**/*.bpe", "*.vocab", "**/*.vocab",
    "README.md", "LICENSE*", "NOTICE*", "*.md", "**/*.md",
]


def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as handle:
        for part in iter(lambda:handle.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()


def validate_model_name(name):
    if name not in MODELS:
        raise ValueError("Yalnız e5-base, minilm veya bge-m3 destekleniyor.")
    return MODELS[name]


def download_model(name, destination=None):
    repo, expected, default = validate_model_name(name)
    folder=Path(destination or default).resolve()
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError("Model klasörü boş olmalı; var olan indirme korunuyor.")
    from huggingface_hub import model_info, snapshot_download
    info=model_info(repo,files_metadata=False)
    license_id=getattr(getattr(info,"card_data",None),"license",None)
    if not license_id or str(license_id).lower()!=expected.lower():
        raise ValueError("Açık lisans kartı doğrulanmadı: "+repo)
    commit=info.sha
    if not commit or len(commit)!=40:
        raise ValueError("Sabit model commit SHA alınamadı.")
    # Only weights/config/tokenizers; ONNX, PyTorch pickle, third-party
    # dataset files, training corpora and untrusted executable code excluded.
    folder.mkdir(parents=True,exist_ok=True)
    snapshot_download(
        repo_id=repo,revision=commit,local_dir=str(folder),
        allow_patterns=ALLOWED,
        ignore_patterns=[
            "*.bin", "**/*.bin", "*.h5", "*.ot", "*.msgpack",
            "onnx/*", "openvino/*", ".eval_results/*", "*.parquet",
            "*.csv", "*.tsv", "*.jsonl", "*.py", "**/*.py",
        ],
    )
    weights=sorted(p for p in folder.rglob("*.safetensors")
                   if ".cache" not in p.parts)
    if not weights:
        raise ValueError("Güvenli safetensors model ağırlığı bulunamadı.")
    metadata={
        "repo":repo, "resolved_revision":commit,
        "declared_license":expected,
        "weights":[{"path":str(p.relative_to(folder)).replace("\\","/"),
                    "bytes":p.stat().st_size,"sha256":sha256_file(p)}
                   for p in weights],
        "downloaded_at_utc":datetime.now(timezone.utc).isoformat(),
        "hf_card_license_checked":True,
        "third_party_dataset_downloaded":False,
        "offline_inference_ready_pending_test":True,
        "commercial_release_approved":False,
    }
    (folder/"faqvec_backbone_origin.json").write_text(
        json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )
    return metadata


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--model",choices=list(MODELS),required=True)
    parser.add_argument("--destination",help="Modelin konacağı BOŞ yerel dizin")
    parser.add_argument("--confirm-download",action="store_true",
                        help="Gerçek model ağırlığı için internet indirmesine açık onay")
    args=parser.parse_args()
    if not args.confirm_download:
        parser.error("İndirme başlatılmadı. İlk indirme için --confirm-download gerekli.")
    meta=download_model(args.model,args.destination)
    print("MODEL_WEIGHTS_DOWNLOADED="+json.dumps({
        "repo":meta["repo"],"revision":meta["resolved_revision"],
        "license":meta["declared_license"],
        "total_weight_bytes":sum(p["bytes"] for p in meta["weights"]),
        "third_party_dataset_downloaded":False,
    },ensure_ascii=True))


if __name__=="__main__":
    main()
