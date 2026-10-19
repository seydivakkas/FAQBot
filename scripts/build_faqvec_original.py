"""FAQVec-TR: yalnız proje için sıfırdan yazılmış Türkçe taslak SSS üretimi.

Girdi: depodaki özgün, kurgusal senaryo kataloğu.
İnternet veya harici korpus indirmez; "hazır eğitim verisi" üretmez.
Niyetleri aynı karıştırılabilir aileyle aynı train/validation/test bölmesine koyar.
"""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, timezone, datetime
from pathlib import Path

from app.faqvec_v2_data import DatasetError, split_intent, validate_intents
from app.matching import normalize

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "seed" / "faqvec_tr_ozgun_taslak_v01.json"
SOURCE_ID = "faqvec-original-project-draft"
FAMILY_SEED = "faqvec-owned-families-v01"
SENSITIVE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|https?://|www\.|\b\d{9,}\b",re.I)

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _jsonl(records):
    return "".join(json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n"
                   for record in records)

def load_original_draft(path=CATALOG):
    path=Path(path)
    content=json.loads(path.read_text(encoding="utf-8"))
    if content.get("schema_version") != 1 or content.get("origin_kind") != "project_authored_draft":
        raise DatasetError("Yalnız proje için yazılan açıkça TASLAK katalog okunabilir.")
    if content.get("commercial_training_approved") is not False:
        raise DatasetError("Taslak veriler ticari onaylı işaretlenemez.")
    originals=content.get("records")
    if not isinstance(originals,list) or len(originals)<16:
        raise DatasetError("En az 16 niyetli özgün katalog gerekir.")
    ids=set()
    texts={}
    families=defaultdict(list)
    checked=[]
    for r in originals:
        intent=r.get("intent_id")
        if not intent or intent in ids:
            raise DatasetError("Niyet kimliği boş veya yinelenmiş.")
        ids.add(intent)
        family=r.get("family_id")
        domain=r.get("domain")
        if not domain or not family or not family.startswith(domain+"-"):
            raise DatasetError("Niyetin alan/aile sözleşmesi geçersiz.")
        if (r.get("source_id") != SOURCE_ID
                or r.get("authorship") != "newly_written_project_draft"
                or r.get("human_review") != "pending"
                or r.get("rights_verified") is not False):
            raise DatasetError("Veri özgün TASLAK köken durumunu korumalı.")
        alts=r.get("alternatives")
        if not isinstance(alts,list) or len(alts)<2:
            raise DatasetError("Her niyette en az iki alternatif soru olmalı.")
        group=[r.get("question"),*alts,r.get("answer")]
        if not all(isinstance(s,str) and s.strip() and len(s)<=800 for s in group):
            raise DatasetError("Soru/alternatif/cevap alanları boş veya aşırı uzun.")
        for text in group[:-1]:
            if SENSITIVE.search(text):
                raise DatasetError("Metinde kişisel iletişim veya gizlilik riski var.")
            token=normalize(text)
            if not token:
                raise DatasetError("Normalizasyon sonrası boş ifade.")
            if token in texts:
                raise DatasetError(
                    "Tekrarlanan ifade bulundu; niyet/soru ayrımını kontrol edin."
                )
            texts[token]=intent
        checked.append(r)
        families[family].append(r)
    if any(len(g)!=2 for g in families.values()):
        raise DatasetError("Her zor negatif senaryo ailesi tam olarak iki farklı niyet taşımalı.")
    return checked

def build_draft(records):
    groups=defaultdict(list)
    for row in records:
        groups[row["family_id"]].append(row)
    intent_rows=[]
    negative=[]
    reviews=[]
    for family,items in sorted(groups.items()):
        split=split_intent(family,FAMILY_SEED)
        assert len(items)==2
        items=sorted(items,key=lambda r:r["intent_id"])
        for row in items:
            item={
                "intent_id":row["intent_id"],"split":split,
                "question":row["question"],"alternatives":row["alternatives"],
                "answer":row["answer"],"domain":row["domain"],
                "family_id":family,"source_id":SOURCE_ID,
                "origin_kind":"project_authored_draft",
                "human_review":"pending",
                "rights_verified":False,
            }
            intent_rows.append(item)
            reviews.append({
                "intent_id":row["intent_id"],"domain":row["domain"],
                "family_id":family,"expected_split":split,
                "review_kind":"positive_paraphrase_and_answer",
                "review_status":"needs_human_review","reviewed_by":None,
                "decision":None,"note":"",
            })
        a,b=items
        negative.append({
            "anchor_intent":a["intent_id"],
            "negative_intent":b["intent_id"],
            "anchor":a["question"],
            "positive":a["alternatives"][0],
            "candidate_negative":b["question"],
            "reason":"Aynı konunun farklı müşteri ihtiyacı; olası yanlış negatifler ayrıca denetlenmeli.",
            "split":split,
            "status":"needs_human_review",
            "reviewed_by":None,
            "human_verified":False,
        })
    validate_intents(intent_rows)
    # Validation/test örnekleri eğitim hard-negative havuzuna eklenmez.
    train_candidates=[x for x in negative if x["split"]=="train"]
    assert all(x["split"]=="train" for x in train_candidates)
    intent_rows.sort(key=lambda x:x["intent_id"])
    negative.sort(key=lambda x:(x["split"],x["anchor_intent"]))
    reviews.sort(key=lambda x:x["intent_id"])
    return intent_rows,negative,reviews,train_candidates

def _save_new(path,content):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise FileExistsError("Var olan taslak ya da inceleme dosyasına yazılmaz: "+str(path))
    path.write_text(content,encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def build_package(*,catalog=CATALOG,output_dir="datasets/faqvec_original_v01"):
    originals=load_original_draft(catalog)
    records,negatives,reviews,train_negatives=build_draft(originals)
    output=Path(output_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Mevcut veri paketi korunur; yeni dizin adı seçin.")
    output.mkdir(parents=True,exist_ok=True)
    catalog_hash=file_hash(catalog)
    payload=_jsonl(records)
    data_hash=_save_new(output/"original_draft.jsonl",payload)
    neg_hash=_save_new(output/"hard_negative_review.DRAFT.jsonl",_jsonl(negatives))
    _save_new(output/"intent_review.DRAFT.jsonl",_jsonl(reviews))
    _save_new(output/"hard_negatives_train_candidate.DRAFT.jsonl",_jsonl(train_negatives))
    proof={
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_type":"original_project_authored_synthetic_draft",
        "catalog_path":"seed/faqvec_tr_ozgun_taslak_v01.json",
        "catalog_sha256":catalog_hash,
        "not_external_dataset":True,
        "no_external_corpus_access":True,
        "copyright_and_semantic_review":"PENDING_HUMAN_REVIEW",
        "rights_review_complete":False,
        "commercial_training_approved":False,
        "note":"Metinler proje için özgün kurgusal taslak olarak yazıldı; mutlak telifsizlik veya insan kalite onayı iddia edilmez.",
    }
    proof_text=json.dumps(proof,ensure_ascii=False,indent=2)+"\n"
    evidence_hash=_save_new(output/"authorship_evidence.DRAFT.json",proof_text)
    splits=Counter(x["split"] for x in records)
    families=Counter(x["family_id"] for x in records)
    manifest={
        "schema_version":1,
        "sources":[{
            "id":SOURCE_ID,
            "origin_url":"local://faqvec/project-authored-synthetic-v01",
            "license_spdx":"OWNED",
            "origin_kind":"self_authored",
            "reviewed_by":None,
            "rights_review_complete":False,
            "rights_evidence_path":"authorship_evidence.DRAFT.json",
            "evidence_sha256":evidence_hash,
            "commercial_training_approved":False,
            "annotation_review":"NOT_REVIEWED",
        }],
        "files":[{"path":"original_draft.jsonl","sha256":data_hash}],
        "original_catalog_sha256":catalog_hash,
        "train_only_hard_negatives":len(train_negatives),
        "negative_review_sha256":neg_hash,
        "split_contract":FAMILY_SEED,
        "commercial_acceptance":"HOLD",
        "model_training":"NOT_ALLOWED_UNTIL_HUMAN_APPROVAL",
    }
    _save_new(output/"manifest.DRAFT.json",json.dumps(
        manifest,ensure_ascii=False,indent=2)+"\n")
    summary={
        "source":"project_authored_fictional_draft",
        "source_catalog_sha256":catalog_hash,
        "intents":len(records),
        "families":len(families),
        "domains":len({row["domain"] for row in records}),
        "positive_paraphrase_pairs":sum(len(r["alternatives"]) for r in records),
        "candidate_hard_negative_pairs":len(negatives),
        "train_only_negative_candidates":len(train_negatives),
        "human_approved_intents":0,
        "human_approved_hard_negatives":0,
        "split_intents":{s:splits[s] for s in ("train","validation","test")},
        "external_dataset_used":False,
        "commercial_acceptance":"HOLD",
    }
    _save_new(output/"summary.json",json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    return summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--catalog",default=str(CATALOG))
    parser.add_argument("--output-dir",default="datasets/faqvec_original_v01")
    parser.add_argument("--check-only",action="store_true",
                        help="Sadece özgün katalog ve sızıntı kontrollerini yap; dosya üretme.")
    args=parser.parse_args()
    if args.check_only:
        recs=load_original_draft(args.catalog)
        intents,negative,_,train=build_draft(recs)
        stats={
            "intents":len(intents),"domains":len(set(r["domain"] for r in intents)),
            "paraphrases":sum(len(r["alternatives"]) for r in intents),
            "candidate_negatives":len(negative),
            "train_negative_candidates":len(train),
            "split_intents":validate_intents(intents),
            "commercial_acceptance":"HOLD",
        }
    else:
        stats=build_package(catalog=args.catalog,output_dir=args.output_dir)
    print("FAQVEC_ORIGINAL_DRAFT="+json.dumps(stats,ensure_ascii=True))

if __name__=="__main__":
    main()
