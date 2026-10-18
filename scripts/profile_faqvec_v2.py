"""FAQVec-TR / E5 / BGE-M3 / MiniLM kaynak profili.

Yalnızca hazır yerel model klasörünü kullanır; model indirmez.
CPU/GPU süreleri, RSS öncesi/sonrası, CUDA peak VRAM ve dosya boyutu ölçülür.
"""
import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path


def model_directory_size(folder):
    return sum(p.stat().st_size for p in Path(folder).rglob("*") if p.is_file())


def percentile(samples, percentile_value):
    ordered = sorted(samples)
    if not ordered:
        return None
    position = (len(ordered) - 1) * percentile_value / 100
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    frac = position - lo
    return ordered[lo] * (1-frac) + ordered[hi] * frac


def snapshot_ram():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss
    except ImportError:
        return None


def run_profile(model_path, questions, *,
                model_name="faqvec-v2", device="cpu", warmup=5,
                batch_size=16, max_questions=100):
    """Sıcak durum tek-soru latency ve batch throughput; eğitim metriği değil."""
    folder = Path(model_path).resolve()
    if not folder.is_dir() or not questions:
        raise ValueError("Hazır model klasörü ve soru listesi gerekli.")
    if device not in ("cpu", "cuda"):
        raise ValueError("Profil cihazı cpu/cuda olabilir.")
    if not 1 <= batch_size <= 128 or not 1 <= max_questions <= 10000:
        raise ValueError("Batch ve soru limitleri geçersiz.")
    import torch
    from sentence_transformers import SentenceTransformer

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA bulunamadı; CUDA başarısı varsayılamaz.")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    model = SentenceTransformer(
        str(folder), device=device,
        local_files_only=True, trust_remote_code=False,
    )
    query_prefix = "query: " if model_name in ("e5-base", "faqvec-v2") else ""
    texts = [query_prefix + x for x in questions[:max_questions]]
    if not texts:
        raise ValueError("Ölçülecek soru yok.")
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    mem_start = snapshot_ram()
    sync = torch.cuda.synchronize if device == "cuda" else (lambda: None)
    for i in range(warmup):
        model.encode([texts[i % len(texts)]], convert_to_numpy=True,
                     show_progress_bar=False)
    sync()
    timings = []
    for text in texts:
        begin = time.perf_counter()
        model.encode([text], convert_to_numpy=True, show_progress_bar=False)
        sync()
        timings.append((time.perf_counter() - begin) * 1000)
    begin = time.perf_counter()
    model.encode(texts, batch_size=batch_size, convert_to_numpy=True,
                 show_progress_bar=False)
    sync()
    batch_duration = time.perf_counter()-begin
    mem_end = snapshot_ram()
    return {
        "model": model_name,
        "local_path": str(folder),
        "device": device,
        "questions": len(texts),
        "warmup": warmup,
        "batch_size": batch_size,
        "single_question_p50_ms": round(percentile(timings,50),2),
        "single_question_p95_ms": round(percentile(timings,95),2),
        "batch_throughput_questions_per_second": round(len(texts)/max(batch_duration,1e-9),2),
        "rss_before_measurement_bytes": mem_start,
        "rss_after_measurement_bytes": mem_end,
        "cuda_peak_allocated_bytes": (
            int(torch.cuda.max_memory_allocated()) if device=="cuda" else None
        ),
        "model_folder_bytes": model_directory_size(folder),
        "measured_utc": datetime.now(timezone.utc).isoformat(),
        "interpretation": "RSS is before/after (NOT maximum). CUDA peak is PyTorch allocator only.",
        "commercial_acceptance": "HOLD",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Yerel model klasörü")
    parser.add_argument("--name", choices=("e5-base","faqvec-v2","bge-m3","minilm"),
                        required=True)
    parser.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    parser.add_argument("--input-file",help="UTF-8, satır başına bir Türkçe soru")
    parser.add_argument("--output", default="reports/faqvec_profile.json")
    parser.add_argument("--batch-size",type=int,default=16)
    args=parser.parse_args()
    if args.input_file:
        texts=[x.strip() for x in Path(args.input_file).read_text(
            encoding="utf-8").splitlines() if x.strip()]
    else:
        from app.faqvec_v2_data import load_bundled_demo
        texts=[r["question"] for r in load_bundled_demo()]
    report=run_profile(args.model,texts,model_name=args.name,
                       device=args.device,batch_size=args.batch_size)
    p=Path(args.output)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(p),"latency_p95_ms":report["single_question_p95_ms"],
                      "commercial_acceptance":"HOLD"},ensure_ascii=True))


if __name__=="__main__":
    main()
