"""D02 legal-provenance evidence completeness check (NOT a legal sign-off).

Never flips dataset commercial_training_approved to true. Evidence source
documents stay local: only hashes/status are written to JSON.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.audit_faqvec_d01 import SOURCE_REPO, SOURCE_SHA, SOURCE_LFS_SHA256

REQUIRED = (
    "creator_or_rights_holder",
    "contact_channel",
    "underlying_sentence_origin",
    "third_party_text_sources",
    "commercial_ml_training_permission",
    "fine_tuned_weight_distribution_permission",
    "license_obligations",
    "independent_legal_reviewer",
    "independent_legal_review_date",
)
DECISIONS = ("granted_with_evidence", "denied", "unknown")


def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def review_evidence(entry, base_folder):
    if not isinstance(entry,dict):
        raise ValueError("Kanıt JSON bir nesne olmalı.")
    if entry.get("source_repo") != SOURCE_REPO or entry.get("source_revision") != SOURCE_SHA:
        raise ValueError("Kaynak sözleşmesinin repo/revizyon kimliği yanlış.")
    if entry.get("source_sha256") != SOURCE_LFS_SHA256:
        raise ValueError("Kanıt farklı veri dosyasına ait.")
    missing=[key for key in REQUIRED if not entry.get(key)]
    records=entry.get("evidence_files",[])
    if not isinstance(records,list):
        raise ValueError("evidence_files listesi gerekli.")
    evidence=[]
    for item in records:
        rel=Path(item.get("path",""))
        if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Kanıt yolu yerel ve güvenli olmalı.")
        path=(Path(base_folder).resolve()/rel).resolve()
        if not path.is_relative_to(Path(base_folder).resolve()):
            raise ValueError("Kanıt dizininin dışına erişilemez.")
        if not path.is_file():
            raise ValueError("Kanıt dosyası bulunamadı.")
        measured=sha256(path)
        if measured != item.get("sha256"):
            raise ValueError("Kanıt SHA-256 uyuşmuyor.")
        evidence.append({"path":str(rel),"sha256":measured})
    training=entry.get("commercial_ml_training_permission","unknown")
    weights=entry.get("fine_tuned_weight_distribution_permission","unknown")
    if training not in DECISIONS or weights not in DECISIONS:
        raise ValueError("İzin değerleri granted_with_evidence / denied / unknown olabilir.")
    blockers=[]
    if missing: blockers.append("Zorunlu alanlar eksik.")
    if not evidence: blockers.append("İmzalı/yazılı kaynak belgesi yok.")
    if training != "granted_with_evidence": blockers.append("Ticari ML eğitimi izin kanıtı eksik.")
    if weights != "granted_with_evidence": blockers.append("Türetilmiş ağırlık dağıtım izin kanıtı eksik.")
    # External, competent rights holder and independent legal review are
    # real-world facts and cannot be verified from a JSON checkbox.
    blockers.append("Belge sahipliği ve hukuki yetki bağımsız incelemede doğrulanmadı.")
    return {
        "source_repo":SOURCE_REPO,"source_revision":SOURCE_SHA,
        "documents_with_correct_sha":evidence,
        "missing_fields":missing,
        "documentary_completeness":bool(not missing and evidence),
        "blockers":blockers,
        "technical_document_check":"PASS" if not missing and evidence else "HOLD",
        "independent_rights_authenticity":"HOLD",
        "commercial_training":"HOLD",
        "commercial_distribution":"HOLD",
        "note":"Dosya ve imza iddialarının gerçek hak sahibinden geldiği bu araçla teyit edilemez.",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence-register",required=True)
    parser.add_argument("--output",default="reports/faqvec-d02/rights_status.json")
    args=parser.parse_args()
    path=Path(args.evidence_register).resolve()
    entry=json.loads(path.read_text(encoding="utf-8"))
    output=review_evidence(entry,path.parent)
    destination=Path(args.output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise FileExistsError("Önceki hak inceleme raporu üzerine yazılamaz.")
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2),
                           encoding="utf-8")
    print("D02_RIGHTS_STATUS="+json.dumps(
        {key:value for key,value in output.items() if key!="documents_with_correct_sha"},
        ensure_ascii=True
    ))


if __name__=="__main__":
    main()
