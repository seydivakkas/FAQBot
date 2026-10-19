"""D04: yalnız özgün AI-denetimli Türkçe soru verileriyle ölçümlü offline yarış.

Gerçek ağırlıklar yoksa sonuç ÜRETMEZ. Aynı kanonik soru galerisi,
validation'da kalibre eşik, dokunulmamış test, OOS/yanlış cevap ölçer.
Kurgusal-AI kökenli testin bağımsız müşteri testi olmadığını vurgular.
"""
import argparse
import gc
import hashlib
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.faqvec_v2_metrics import (
    evaluate_matrix, thresholds_on_validation, paired_intent_bootstrap_recall_delta,
)
from app.faqvec_v2_data import validate_intents
from app.matching import normalize
from scripts.faqvec_d03_ai_review import evaluate, INTENT_BLOB, OOS_BLOB

SUPPORTED={"e5-base","faqvec-tr","bge-m3","minilm"}
E5={"e5-base","faqvec-tr"}


def build_research_suite():
    records, _reviewed, _negatives, no_answer, _stats=evaluate()
    validate_intents(records)
    gallery_ids=sorted(row["intent_id"] for row in records)
    by_id={row["intent_id"]:row for row in records}
    gallery=[by_id[ident]["question"] for ident in gallery_ids]
    queries={"validation":[],"test":[]}
    for row in records:
        if row["split"] not in queries:
            continue
        for candidate in row["alternatives"]:
            queries[row["split"]].append({
                "query":candidate,
                "expected_id":row["intent_id"],
                "source":"project_ai_reviewed_paraphrase",
            })
    usable=[r for r in no_answer
            if r["ai_decision"]=="no_answer_research_candidate"]
    if len(usable)!=22:
        raise ValueError("Yalnız 22 AI kontrollü no-answer örneği bekleniyor.")
    # Hash sırasına dayalı ayrım, ilk 11 validation, kalan 11 test.
    # Bu veri model ağırlıkları veya skorları görülmeden kaynak üzerinden sabitlenir.
    ranked=sorted(usable,key=lambda r:hashlib.sha256(
        ("faqvec-d04-oos-v01:"+r["candidate_id"]).encode("utf-8")
    ).hexdigest())
    taken=set()
    for i,record in enumerate(ranked):
        query=record["query"]
        if normalize(query) in taken or normalize(query) in {normalize(x) for x in gallery}:
            raise ValueError("Galeri/OOS test veri çakışması.")
        taken.add(normalize(query))
        split="validation" if i<11 else "test"
        queries[split].append({
            "query":query,"expected_id":None,
            "source":"project_ai_reviewed_no_answer",
        })
    for split in queries:
        queries[split].sort(key=lambda q:(q["source"],q["query"]))
        if not any(q["expected_id"] is None for q in queries[split]):
            raise ValueError("Eşik kalibrasyonu için no-answer örneği bulunmalı.")
        if not any(q["expected_id"] is not None for q in queries[split]):
            raise ValueError("Pozitif retrieval örnekleri eksik.")
    return gallery_ids,gallery,queries


def _quantile(vals,p):
    if not vals:
        return None
    return round(float(np.quantile(np.asarray(vals,dtype=float),p)),2)


def _model_disk_bytes(folder):
    return sum(p.stat().st_size for p in Path(folder).rglob("*")
               if p.is_file() and ".cache" not in p.parts)


def _rss_megabytes():
    try:
        import psutil
        return round(psutil.Process().memory_info().rss/1024**2,1)
    except ImportError:
        return None


def _device_memory():
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.max_memory_allocated()/1024**2,1)
    except ImportError:
        return None
    return None


def compute_scores(name,folder,gallery,queries,*,latency_samples=8,batch_size=8):
    vals, tst=queries["validation"],queries["test"]
    if name=="tfidf":
        clock=time.perf_counter()
        vectorizer=TfidfVectorizer(analyzer="char_wb",ngram_range=(2,5),
                                   lowercase=False,sublinear_tf=True)
        gallery_vec=vectorizer.fit_transform([normalize(x) for x in gallery])
        fit_sec=time.perf_counter()-clock
        start=time.perf_counter()
        val_m=cosine_similarity(
            vectorizer.transform([normalize(x["query"]) for x in vals]),gallery_vec)
        test_m=cosine_similarity(
            vectorizer.transform([normalize(x["query"]) for x in tst]),gallery_vec)
        query_sec=time.perf_counter()-start
        durations=[]
        for q in (vals+tst)[:latency_samples]:
            tic=time.perf_counter()
            vectorizer.transform([normalize(q["query"])])
            durations.append((time.perf_counter()-tic)*1000)
        return val_m,test_m,{
            "model_loading_seconds":round(fit_sec,3),
            "batch_query_seconds":round(query_sec,3),
            "per_query_latency_p50_ms":_quantile(durations,.5),
            "per_query_latency_p95_ms":_quantile(durations,.95),
            "latency_sample_count":len(durations),
            "ram_rss_mb_after":_rss_megabytes(),
            "gpu_max_allocated_mb":None,
            "local_model_file_bytes":None,
            "device":"cpu",
            "local_weight_revision":None,
        }
    target=Path(folder).resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"Yerel model ağırlıkları yok: {target}")
    if name not in SUPPORTED:
        raise ValueError("Desteklenmeyen model.")
    prefix="query: " if name in E5 else ""
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(min(4,torch.get_num_threads()))
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    device="cuda" if torch.cuda.is_available() else "cpu"
    tic=time.perf_counter()
    model=SentenceTransformer(
        str(target),device=device,
        local_files_only=True,trust_remote_code=False,
    )
    loading_sec=time.perf_counter()-tic
    def encode(texts):
        vectors=model.encode(
            [prefix+x for x in texts],
            batch_size=batch_size,normalize_embeddings=True,
            convert_to_numpy=True,show_progress_bar=False,
        )
        return np.asarray(vectors,dtype=np.float32)
    with torch.inference_mode():
        gallery_vec=encode(gallery)
        start=time.perf_counter()
        vals_vec=encode([x["query"] for x in vals])
        tst_vec=encode([x["query"] for x in tst])
        query_sec=time.perf_counter()-start
        val_m=vals_vec @ gallery_vec.T
        test_m=tst_vec @ gallery_vec.T
        durations=[]
        for q in (vals+tst)[:latency_samples]:
            before=time.perf_counter()
            encode([q["query"]])
            if device=="cuda":
                torch.cuda.synchronize()
            durations.append((time.perf_counter()-before)*1000)
    rss=_rss_megabytes()
    gpu=_device_memory()
    disk=_model_disk_bytes(target)
    meta=target/"faqvec_backbone_origin.json"
    revision=None
    if meta.is_file():
        revision=json.loads(meta.read_text(encoding="utf-8")).get("resolved_revision")
    if name=="faqvec-tr":
        training_meta=target/"faqvec_v2_manifest.json"
        if not training_meta.is_file():
            raise ValueError("Gerçek fine-tune meta kaydı olmayan model FAQVec-TR sayılmaz.")
        saved=json.loads(training_meta.read_text(encoding="utf-8"))
        if saved.get("source_mode")!="ai_reviewed_project_owned_research_only" or (
                saved.get("research_only") is not True):
            raise ValueError("FAQVec-TR kaynak ve araştırma modu kanıtı eksik.")
        revision=saved.get("backbone",{}).get("resolved_revision")
    del model
    gc.collect()
    if device=="cuda":
        torch.cuda.empty_cache()
    return val_m,test_m,{
        "model_loading_seconds":round(loading_sec,3),
        "batch_query_seconds":round(query_sec,3),
        "per_query_latency_p50_ms":_quantile(durations,.5),
        "per_query_latency_p95_ms":_quantile(durations,.95),
        "latency_sample_count":len(durations),
        "ram_rss_mb_after":rss,
        "gpu_max_allocated_mb":gpu,
        "local_model_file_bytes":disk,
        "device":device,
        "local_weight_revision":revision,
    }


def compare(models,*,latency_samples=8,batch_size=8):
    ids,gallery,queries=build_research_suite()
    val,test=queries["validation"],queries["test"]
    labels_val=[q["expected_id"] for q in val]
    labels_test=[q["expected_id"] for q in test]
    test_scores={}
    report={
        "stage":"FAQVec-TR-D04",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_intent_git_blob":INTENT_BLOB,
        "source_no_answer_git_blob":OOS_BLOB,
        "source_policy":"project-authored synthetic FAQ only",
        "human_labeling_performed":False,
        "labels_source":"AI reviewed original project data",
        "independent_customer_test":False,
        "research_only":True,
        "commercial_acceptance":"HOLD",
        "gallery_size":len(ids),
        "validation_queries":len(val),
        "test_queries":len(test),
        "validation_oos":sum(label is None for label in labels_val),
        "test_oos":sum(label is None for label in labels_test),
        "oos_split_contract":"sha256-faqvec-d04-oos-v01-11-validation-11-test",
        "environment":{
            "python":platform.python_version(),
            "platform":platform.platform(),
            "latency_sample_count":latency_samples,
            "inference_batch_size":batch_size,
        },
        "models":[],
    }
    for name,path in models:
        valid,test_matrix,speed=compute_scores(
            name,path,gallery,queries,
            latency_samples=latency_samples,batch_size=batch_size,
        )
        threshold=thresholds_on_validation(valid,ids,labels_val)
        scores=evaluate_matrix(test_matrix,ids,labels_test,threshold)
        model_result={
            "name":name,
            "measured_real_model":name!="tfidf",
            "local_path":str(Path(path).resolve()) if path else None,
            "threshold_from_validation_only":threshold,
            "quality":scores,
            "performance":speed,
        }
        report["models"].append(model_result)
        test_scores[name]=test_matrix
    if "tfidf" in test_scores:
        for row in report["models"]:
            if row["name"]!="tfidf":
                row["paired_vs_tfidf"]=paired_intent_bootstrap_recall_delta(
                    test_scores["tfidf"],test_scores[row["name"]],
                    ids,labels_test,
                )
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ai-owned-research",action="store_true",required=True,
                        help="Kendi yazılan AI-denetimli veri dışında benchmark yasak")
    parser.add_argument("--model",action="append",default=[],help="e5-base=/yerel/yol veya faqvec-tr=...")
    parser.add_argument("--output",default="reports/faqvec_d04_measured.json")
    parser.add_argument("--latency-samples",type=int,default=8)
    parser.add_argument("--batch-size",type=int,default=8)
    args=parser.parse_args()
    if not 1<=args.latency_samples<=100 or not 1<=args.batch_size<=32:
        parser.error("Ölçüm sayı/batch sınırı aşıldı.")
    specs=[("tfidf",None)]
    seen={"tfidf"}
    for raw in args.model:
        if "=" not in raw:
            parser.error("--model name=local-folder şeklinde verilmeli.")
        name,path=raw.split("=",1)
        if name not in SUPPORTED or name in seen or not path:
            parser.error("Model adı/sırası geçersiz veya yinelenmiş.")
        seen.add(name)
        specs.append((name,path))
    os.environ.update({
        "HF_HUB_OFFLINE":"1",
        "TRANSFORMERS_OFFLINE":"1",
        "WANDB_DISABLED":"true",
    })
    result=compare(specs,latency_samples=args.latency_samples,batch_size=args.batch_size)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        raise FileExistsError("Eski ölçüm raporunun üzerine yazılmaz.")
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("D04_RESULTS="+json.dumps({
        "models":[{"name":v["name"],
                   "recall_at_1":v["quality"]["recall_at_1"],
                   "wrong_match_rate":v["quality"]["wrong_match_rate"],
                   "false_answer_rate":v["quality"]["false_answer_rate"],
                   "no_answer_accuracy":v["quality"]["no_answer_accuracy"]}
                  for v in result["models"]],
        "gallery":result["gallery_size"],
        "validation_queries":result["validation_queries"],
        "test_queries":result["test_queries"],
        "commercial_acceptance":result["commercial_acceptance"],
    },ensure_ascii=True))


if __name__=="__main__":
    main()
