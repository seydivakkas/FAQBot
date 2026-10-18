"""FAQVec-TR D02: evidence and two-review readiness, never forge human/legal PASS.

Outputs technical readiness only. Real identity, rights ownership, legal
authorization, and semantic quality remain independently verified tasks.
"""
import argparse
import json
from pathlib import Path

from scripts.audit_faqvec_d01 import SOURCE_LFS_SHA256, SOURCE_SHA
from scripts.faqvec_d02_review import aggregate, digest, validate_bundle
from scripts.faqvec_d02_rights import review_evidence


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assess(*, bundle_path=None, freeze_path=None,
           review_a_path=None, review_b_path=None, rights_path=None):
    failures=[]
    checks={}
    bundle=None
    freeze=None

    if not bundle_path:
        failures.append("Özgün sabit kaynakla üretilmiş inceleme görev paketi yok.")
        checks["bundle"]="HOLD"
    else:
        try:
            bundle=_read(bundle_path)
            validate_bundle(bundle)
            if bundle["source_sha256"] != SOURCE_LFS_SHA256 or bundle["source_revision"] != SOURCE_SHA:
                raise ValueError("Kaynak revizyon/hash uyuşmazlığı")
            checks["bundle"]="PASS"
        except (OSError,KeyError,ValueError,TypeError) as exc:
            failures.append("D02 görev paketi bütünlüğü doğrulanamadı: "+str(exc))
            checks["bundle"]="HOLD"
            bundle=None

    if not freeze_path:
        failures.append("Kaynağa bağlı sabit test adayı kimlikleri yok.")
        checks["frozen_test_candidates"]="HOLD"
    else:
        try:
            freeze=_read(freeze_path)
            saved=freeze.pop("freeze_sha256")
            valid=digest(freeze)==saved
            freeze["freeze_sha256"]=saved
            if (not valid or freeze.get("source_sha256") != SOURCE_LFS_SHA256 or
                    freeze.get("source_revision") != SOURCE_SHA or
                    freeze.get("usable_for_final_acceptance") is not False or
                    freeze.get("candidate_only") is not True or
                    not isinstance(freeze.get("test_candidate_intent_ids"),list)):
                raise ValueError("Sabit aday test sözleşmesi veya SHA geçersiz")
            if bundle and freeze["source_sha256"] != bundle["source_sha256"]:
                raise ValueError("Görev ve test kaynağı uyuşmuyor")
            checks["frozen_test_candidates"]="PASS_CANDIDATES_ONLY"
        except (OSError,KeyError,ValueError,TypeError) as exc:
            failures.append("Test aday listesi doğrulanamadı: "+str(exc))
            checks["frozen_test_candidates"]="HOLD"

    if not (bundle and review_a_path and review_b_path):
        failures.append("İki farklı insan incelemecisinin karar JSON dosyaları eksik.")
        checks["two_independent_review_files"]="HOLD"
    else:
        try:
            report=aggregate(bundle,_read(review_a_path),_read(review_b_path))
            disagreements=sum(report["outcomes"].get(x,0)
                              for x in ("pending","disagreement","uncertain"))
            if disagreements:
                failures.append(f"{disagreements} görev eksik/kararsız/çelişkili; hakem incelemesi gerekli.")
                checks["two_independent_review_files"]="PARTIAL"
            else:
                checks["two_independent_review_files"]="TWO_MATCHING_REVIEW_FILES"
                failures.append("İncelemeci kimlikleri ve etiket doğruluğu bağımsız doğrulanmadı.")
            checks["human_approved_hard_negatives"]=0
            checks["human_review_outcomes"]=report["outcomes"]
        except (OSError,KeyError,ValueError,TypeError) as exc:
            checks["two_independent_review_files"]="HOLD"
            failures.append("İnsan karar dosyaları geçersiz: "+str(exc))

    if not rights_path:
        failures.append("Kaynak sahibinden doğrulanabilir hak/izin belgeleri gelmedi.")
        checks["rights_documents"]="HOLD"
    else:
        try:
            path=Path(rights_path).resolve()
            record=review_evidence(_read(path),path.parent)
            checks["rights_documents"]=record["technical_document_check"]
            if record["technical_document_check"] != "PASS":
                failures.append("Ticari eğitim/dağıtım izin belgelerinin teknik kaydı tamamlanmamış.")
            failures.append("Hak sahipliği ve belgenin hukuki geçerliliği bağımsız doğrulanmadı.")
        except (OSError,KeyError,ValueError,TypeError) as exc:
            checks["rights_documents"]="HOLD"
            failures.append("Belge kanıtı geçersiz: "+str(exc))

    checks["independent_legal_signoff"]="HOLD"
    checks["independent_semantic_signoff"]="HOLD"
    checks["commercial_E5_fine_tuning"]="BLOCKED"
    checks["model_accuracy_claim"]="HOLD"
    checks["customer_distribution"]="HOLD"
    return {
        "stage":"FAQVec-TR-V2-D02",
        "source_revision":SOURCE_SHA,
        "source_sha256":SOURCE_LFS_SHA256,
        "checks":checks,
        "blockers":failures,
        "d02_closed":False,
        "commercial_training_approved":False,
        "note":(
            "Teknik veri dosyası kontrolleri gerçek izinleri, iki insanın "
            "bağımsızlığını veya etiketlerin semantik doğruluğunu otomatik onaylamaz."
        ),
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--bundle")
    parser.add_argument("--freeze")
    parser.add_argument("--review-a")
    parser.add_argument("--review-b")
    parser.add_argument("--rights")
    parser.add_argument("--output",default="reports/faqvec-d02/acceptance_status.json")
    parser.add_argument("--require-commercial-pass",action="store_true",
                        help="Kabul tamamlanmadıysa hata koduyla durdur.")
    args=parser.parse_args()
    report=assess(bundle_path=args.bundle,freeze_path=args.freeze,
                  review_a_path=args.review_a,review_b_path=args.review_b,
                  rights_path=args.rights)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        raise FileExistsError("Kanıt raporu üzerine yazılmaz; sürüm/tarihe özel yeni yol kullanın.")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("D02_ACCEPTANCE="+json.dumps(report,ensure_ascii=True))
    if args.require_commercial_pass and not report["commercial_training_approved"]:
        raise SystemExit("D02 kabulü kapanmadı. Ticari E5 eğitimi engellendi.")


if __name__=="__main__":
    main()
