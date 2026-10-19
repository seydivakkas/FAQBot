"""FAQVec D03-02: AI incelemesi; asla insan/ticari onay iddiası üretmez."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from app.faqvec_v2_data import DatasetError, split_intent, validate_intents
from scripts.build_faqvec_original import (
    CATALOG, OOS_CATALOG, SOURCE_ID, FAMILY_SEED,
    load_original_draft, load_no_answer_draft, _save_new, _jsonl
)

INTENT_BLOB="d82e148c8d203d3bb5732c5f64b8e2bccd757f6a"
OOS_BLOB="ba6a246ce0fda3fcd107f813600b5cd0d3da9449"
REVIEWER="AI:ChatGPT-GPT-6"
CORRECTIONS={
    "siparis-03":{"question":"Siparişim kargoya verilmeden iptal talebi oluşturabilir miyim?",
                  "alternatives":["Henüz gönderilmemiş siparişimi nasıl iptal ettirebilirim?","Ürün yola çıkmadan siparişten vazgeçebilir miyim?"]},
    "kargo-05":{"alternatives":["Taşıyıcıya teslim edilen paketin adresi değiştirilebilir mi?","Dağıtıma çıkmış pakette adres düzeltme isteği nasıl verilir?"]},
    "degisim-01":{"alternatives":["Aldığım beden yerine daha büyük beden isteyebilir miyim?","Beden değişimi isteğini nereden oluştururum?"]},
    "urun-04":{"alternatives":["Kıyafet ölçü kılavuzu hangi sayfada?","Uygun bedeni seçmek için ürünün beden tablosuna nereden bakarım?"]},
    "teslimat-01":{"alternatives":["Teslim alma noktası üzerinden kargo alabilir miyim?","Ev yerine teslimat noktası seçebilir miyim?"]},
    "teslimat-04":{"alternatives":["Yaşadığım bölgeye gönderim var mı nasıl anlarım?","İlçemin teslimat kapsamına girip girmediğini nereden kontrol ederim?"]},
    "teslimat-07":{"alternatives":["Kuryenin yaklaşık hangi saatlerde geleceğini nereden öğrenirim?","Teslimat için tahmini saat aralığını nerede görüntülerim?"]},
    "destek-02":{"alternatives":["Destek biletimin hangi aşamada olduğunu nereden kontrol ederim?","Yardım başvurumun ilerleyişini nasıl takip ederim?"]},
    "fatura-06":{"question":"Belgemin e-arşiv fatura olduğunu nasıl anlarım?",
                 "alternatives":["E-arşiv faturayı belgenin hangi alanından tanıyabilirim?","Elektronik fatura türünü belge üzerinde nereden kontrol ederim?"]},
    "gizlilik-04":{"alternatives":["Kişisel veri düzeltme talebi nasıl açılır?","Hakkımda tutulan yanlış veriyi düzeltmelerini nasıl isteyebilirim?"]},
    "gizlilik-05":{"question":"Verdiğim açık rızayı nasıl geri çekebilirim?",
                  "alternatives":["Açık rızamı nasıl iptal edebilirim?","Kişisel verilerim için verdiğim onayı geri almak istiyorum, ne yapayım?"]},
}
HARD={
    "siparis":(1,2,3),"kargo":(1,2,3),"iade":(1,2,3),
    "degisim":(1,),"odeme":(1,3),"uyelik":(1,4),
    "kampanya":(1,2),"urun":(1,2,3),"teslimat":(1,3,4),
    "destek":(1,2),"fatura":(2,3),"gizlilik":(1,3),
}
EXCLUDE_OOS={"oos-kampanya-2","oos-teslimat-2"}


def blob_sha(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def evaluate():
    if blob_sha(CATALOG)!=INTENT_BLOB or blob_sha(OOS_CATALOG)!=OOS_BLOB:
        raise DatasetError("AI tarafından okunmamış kaynak sürümü; inceleme yeniden yapılmalı.")
    records=load_original_draft()
    expected={f"{d}-{i:02d}" for d in HARD for i in range(1,9)}
    if len(records)!=96 or {r["intent_id"] for r in records}!=expected:
        raise DatasetError("Kaynak kayıt listesi değişmiş.")
    revised=[]
    groups=defaultdict(list)
    for item in records:
        updated=dict(item)
        updated.update(CORRECTIONS.get(item["intent_id"],{}))
        updated["human_review"]="not_performed"
        updated["rights_verified"]=False
        updated["ai_review"]={
            "reviewer":REVIEWER,"date":"2026-10-19",
            "decision":"accepted_for_research",
            "corrected":item["intent_id"] in CORRECTIONS}
        revised.append(updated)
        groups[item["family_id"]].append(updated)
    rows=[]
    for item in revised:
        rows.append({
            "intent_id":item["intent_id"],
            "split":split_intent(item["family_id"],FAMILY_SEED),
            "question":item["question"],"alternatives":item["alternatives"],
            "answer":item["answer"],"source_id":SOURCE_ID,
            "family_id":item["family_id"],"domain":item["domain"],
            "ai_review_status":"accepted_for_research",
            "rights_verified":False,
        })
    splits=validate_intents(rows)
    negatives=[]
    for family,parts in sorted(groups.items()):
        if len(parts)!=2:
            raise DatasetError("Ailede iki farklı niyet olmalı.")
        a,b=sorted(parts,key=lambda p:p["intent_id"])
        hard=int(family.rsplit("-",1)[1]) in HARD[a["domain"]]
        negatives.append({
            "anchor_intent":a["intent_id"],"negative_intent":b["intent_id"],
            "split":split_intent(family,FAMILY_SEED),
            "ai_decision":"hard_negative_candidate" if hard else "ordinary_negative",
            "different_answers":True,"reviewed_by":REVIEWER,
            "human_verified":False,"status":"research_only",
        })
    oos=load_no_answer_draft(intent_records=rows)
    oos_review=[]
    for candidate in oos:
        r=dict(candidate)
        r["ai_decision"]=("excluded_unrealistic" if r["candidate_id"] in EXCLUDE_OOS
                           else "no_answer_research_candidate")
        r["reviewer"]=REVIEWER
        r["human_verified"]=False
        r["commercial_training_approved"]=False
        oos_review.append(r)
    counts={
        "intents_ai_reviewed":len(revised),
        "alternative_questions":sum(len(x["alternatives"]) for x in revised),
        "intent_corrections":sum(bool(x["ai_review"]["corrected"]) for x in revised),
        "negative_pairs_reviewed":len(negatives),
        "hard_negative_candidates":sum(x["ai_decision"]=="hard_negative_candidate" for x in negatives),
        "ordinary_negatives":sum(x["ai_decision"]=="ordinary_negative" for x in negatives),
        "oos_ai_reviewed":len(oos_review),
        "oos_candidates":sum(x["ai_decision"]=="no_answer_research_candidate" for x in oos_review),
        "oos_excluded":sum(x["ai_decision"]=="excluded_unrealistic" for x in oos_review),
        "splits":splits,"human_review_count":0,
        "commercial_training_approved":False,
    }
    assert (counts["intents_ai_reviewed"],counts["intent_corrections"],
            counts["hard_negative_candidates"],counts["ordinary_negatives"],
            counts["oos_candidates"],counts["oos_excluded"])==(96,11,28,20,22,2)
    return rows,revised,negatives,oos_review,counts


def export(destination):
    rows,revised,negatives,oos,counts=evaluate()
    folder=Path(destination).resolve()
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError("Önceki AI değerlendirmesi üzerine yazılmaz.")
    folder.mkdir(parents=True,exist_ok=True)
    files=[]
    for name,values in [
        ("faq.AI_RESEARCH.jsonl",rows),
        ("positive_ai_review.jsonl",revised),
        ("negative_ai_review.jsonl",negatives),
        ("no_answer_ai_review.jsonl",oos),
    ]:
        files.append({"path":name,"sha256":_save_new(folder/name,_jsonl(values))})
    manifest={
        "schema_version":2,"source":SOURCE_ID,
        "origin":"newly_written_project_synthetic_corpus",
        "original_intent_git_blob":INTENT_BLOB,
        "original_no_answer_git_blob":OOS_BLOB,
        "reviewer_type":"AI","reviewer":REVIEWER,
        "independent_human_review":False,
        "only_research":True,
        "rights_review_complete":False,
        "commercial_training_approved":False,
        "files":files,"counts":counts,
    }
    _save_new(folder/"manifest.AI_RESEARCH_ONLY.json",json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    return counts


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check-only",action="store_true")
    parser.add_argument("--output-dir",default="datasets/faqvec_ai_review_v02")
    args=parser.parse_args()
    result=evaluate()[-1] if args.check_only else export(args.output_dir)
    print("D03_AI_REVIEW="+json.dumps(result,ensure_ascii=True))


if __name__=="__main__":
    main()
