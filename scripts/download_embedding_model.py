"""Kullanıcı çağırdığında açık kaynak çok dilli modeli bir kez indirir.

Normal FAQBot sohbeti, benzerlik taraması ve servis başlangıcı internet kullanmaz.
"""
from pathlib import Path

from app.database import ROOT

REPO_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TARGET = ROOT / "models" / "paraphrase-multilingual-MiniLM-L12-v2"


def main():
    print("Yerel model kurulumu açık kullanıcı komutuyla başlatılıyor.")
    print("Kaynak:", REPO_ID)
    print("Hedef klasör:", TARGET)
    print("Bu işlem model dosyalarını indirmek için bir kez internet gerektirir.")
    from huggingface_hub import snapshot_download

    TARGET.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=REPO_ID, local_dir=str(TARGET))
    if not (TARGET / "modules.json").is_file():
        raise RuntimeError("Model kurulumu eksik: modules.json bulunamadı.")
    print("Model indirildi. Ayarlar > Benzer Sorular bölümünde embedding seçilebilir.")


if __name__ == "__main__":
    main()
