"""FAQVec-TR v0.2: MIT E5-base ağırlıklarını denetimli Türkçe SSS ile ince ayar.

- Model ağırlıkları yalnızca önceden açıkça indirilmiş yerel klasörden yüklenir.
- Veri, niyet düzeyinde train/validation/test olarak ayrılır.
- MultipleNegativesRankingLoss + NO_DUPLICATES sampler.
- Zor negatifler ancak ayrı dosyada insan onaylıysa ikinci aşamada kullanılır.
- Ticari eğitim için açık izinli veri manifesti zorunlu.
"""
import argparse
import hashlib
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from app.faqvec_v2_data import (
    load_bundled_demo, load_approved_sources, positive_pairs,
    approved_triplets, validate_intents, write_candidate_negatives,
)

def load_local_backbone(directory):
    path = Path(directory).resolve()
    if not path.is_dir():
        raise RuntimeError("Yerel E5-base klasörü yok; indirmeyi ayrı komutla başlatın.")
    origin = path / "faqvec_backbone_origin.json"
    if not origin.is_file():
        raise RuntimeError("E5 modeli için MIT lisans ve revizyon kayıt dosyası yok.")
    meta = json.loads(origin.read_text(encoding="utf-8"))
    if meta.get("repo") != "intfloat/multilingual-e5-base" or meta.get("declared_license") != "MIT":
        raise RuntimeError("Beklenmeyen ağırlık kaynağı veya lisans.")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(
        str(path), local_files_only=True, trust_remote_code=False
    ), meta


def train():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", default="models/e5-base-original")
    parser.add_argument("--manifest", help="Ticari incelemesi yapılmış JSONL veri kaynak manifesti")
    parser.add_argument("--ai-owned-research", action="store_true",
                        help="Sıfırdan yazılan ve AI tarafından incelenmiş D03 v02 ile yalnız araştırma eğitimi")
    parser.add_argument("--include-ai-negatives", action="store_true",
                        help="Sadece araştırmada, AI seçimi 28 hard adayın train bölümündekilerini kullan")
    parser.add_argument("--demo", action="store_true",
                        help="Yalnızca kurgusal 110 SSS ile deney. Ticari izin değildir.")
    parser.add_argument("--commercial", action="store_true",
                        help="Hakları onaylanmamış veriyle eğitimi kesinlikle reddet")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hard-negatives", help="Sadece approved + reviewed_by triplet")
    parser.add_argument("--suggest-negatives", help="Taslak hard-negative adayları JSONL dosyası")
    parser.add_argument("--output", default="models/faqvec-tr-v0.2-e5")
    args = parser.parse_args()
    if sum((bool(args.demo), bool(args.manifest), bool(args.ai_owned_research))) != 1:
        parser.error("Tam olarak biri seçilmeli: --ai-owned-research, --manifest veya --demo.")
    if args.ai_owned_research and args.commercial:
        parser.error("AI değerlendirmesi bağımsız insan/hukuki onay değildir; ticari eğitim yasak.")
    if args.include_ai_negatives and not args.ai_owned_research:
        parser.error("AI negatifleri yalnız --ai-owned-research modunda kullanılabilir.")
    if args.ai_owned_research and args.hard_negatives:
        parser.error("Bu modda dış/human-approved negatif dosyası yerine yalnız sabit AI adayları kullanılabilir.")
    if args.demo:
        parser.error("Önceki 110 SSS demosu OWNED/CC0 koşulunu karşılamıyor; eğitim için insan onaylı özgün manifest gerekli.")
    if args.commercial and args.demo:
        parser.error("Demo veriler ticari eğitim için onaylı değildir.")
    if args.epochs < 1 or args.epochs > 20 or not 1 <= args.batch_size <= 64:
        parser.error("Epoch 1–20 ve batch-size 1–64 olmalı.")
    if args.gradient_accumulation < 1:
        parser.error("Gradient accumulation 1 veya daha büyük olmalı.")
    ai_negatives = []
    if args.ai_owned_research:
        from scripts.faqvec_d03_ai_review import evaluate
        rows, _reviewed, ai_negatives, _oos, ai_counts = evaluate()
        manifest = {
            "schema_version": 2,
            "source_type": "original_project_authored_ai_reviewed",
            "reviewer_type": "AI",
            "human_review_performed": False,
            "commercial_training_approved": False,
            "rights_review_complete": False,
            "metrics": ai_counts,
        }
        source_mode = "ai_reviewed_project_owned_research_only"
    elif args.manifest:
        rows, manifest = load_approved_sources(args.manifest,
                                               for_commercial=args.commercial)
        source_mode = "approved_manifest" if args.commercial else "research_manifest"
    else:
        rows = load_bundled_demo()
        manifest = None
        source_mode = "bundled_demo_not_commercially_cleared"
    split_stats = validate_intents(rows)
    if min(split_stats.values()) < 1:
        raise RuntimeError("Train/validation/test niyet gruplarının her biri dolu olmalı.")
    pairs = positive_pairs(rows)
    if len(pairs) < 8:
        raise RuntimeError("En az 8 farklı niyetten pozitif eğitim çifti gerekli.")
    if args.ai_owned_research:
        triplets = []
        if args.include_ai_negatives:
            train_intents = {
                item["intent_id"]: item for item in rows if item["split"] == "train"
            }
            for item in ai_negatives:
                if (item["ai_decision"] != "hard_negative_candidate"
                        or item["split"] != "train"):
                    continue
                a = train_intents[item["anchor_intent"]]
                b = train_intents[item["negative_intent"]]
                triplets.append({
                    "anchor": a["question"],
                    "positive": a["alternatives"][0],
                    "negative": b["question"],
                })
    else:
        triplets = approved_triplets(args.hard_negatives, rows)
    if args.suggest_negatives:
        count = write_candidate_negatives(rows, args.suggest_negatives)
        print("Human-review candidate hard negatives:", count)

    # Ağ yolunun hiçbir eğitim aşamasında kullanılmasını önle.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["WANDB_DISABLED"] = "true"
    random.seed(args.seed)
    model, origin = load_local_backbone(args.backbone)
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformerTrainer, SentenceTransformerTrainingArguments, losses,
    )
    from sentence_transformers.training_args import BatchSamplers

    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Çıktı dizini boş olmalı; önceki ağırlıkların üzerine yazılmaz.")
    output.mkdir(parents=True, exist_ok=True)
    # E5 simetrik soru/soru görevinde her iki cümleye de 'query:' öneki gerekir.
    examples = [{"anchor": "query: " + row["anchor"],
                 "positive": "query: " + row["positive"]} for row in pairs]
    ds = Dataset.from_list(examples)
    training_args = SentenceTransformerTrainingArguments(
        output_dir=str(output / "training_checkpoint"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=1e-5, warmup_ratio=0.1,
        fp16=False, bf16=False, dataloader_drop_last=False,
        batch_sampler=BatchSamplers.NO_DUPLICATES, seed=args.seed,
        save_strategy="no", report_to="none",
    )
    trainer = SentenceTransformerTrainer(
        model=model, args=training_args, train_dataset=ds,
        loss=losses.MultipleNegativesRankingLoss(model),
    )
    trainer.train()

    # Ayrı onaylı zor negatif varsa bunu ek eğitim aşaması olarak işle.
    if triplets:
        triplet_ds = Dataset.from_list([{
            "anchor": "query: " + x["anchor"],
            "positive": "query: " + x["positive"],
            "negative": "query: " + x["negative"],
        } for x in triplets])
        hard_args = SentenceTransformerTrainingArguments(
            output_dir=str(output / "hard_negative_checkpoint"),
            num_train_epochs=1, per_device_train_batch_size=min(args.batch_size, 8),
            gradient_accumulation_steps=args.gradient_accumulation,
            learning_rate=5e-6, warmup_ratio=0.0,
            fp16=False, bf16=False,
            batch_sampler=BatchSamplers.NO_DUPLICATES,
            seed=args.seed, save_strategy="no", report_to="none",
        )
        SentenceTransformerTrainer(
            model=model, args=hard_args, train_dataset=triplet_ds,
            loss=losses.MultipleNegativesRankingLoss(model)
        ).train()

    model_dir = output / "model"
    model.save(str(model_dir), safe_serialization=True)
    metadata = {
        "model": "FAQVec-TR v0.2 E5 fine-tune (MIT derivative)",
        "model_license": "MIT (check upstream notices)",
        "backbone": origin,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "source_mode": source_mode,
        "reviewer_type": "AI" if args.ai_owned_research else None,
        "independent_human_review": False if args.ai_owned_research else None,
        "research_only": bool(args.ai_owned_research),
        "ai_negative_candidates_used": len(triplets) if args.ai_owned_research else 0,
        "commercial_training_approved": bool(args.commercial),
        "commercial_acceptance": "HOLD",
        "train_pairs": len(pairs), "approved_triplets": len(triplets),
        "split_intents": split_stats, "epochs": args.epochs,
        "data_manifest": str(Path(args.manifest).resolve()) if args.manifest else None,
        "test_data_used_for_training": False,
        "validation_data_used_for_training": False,
        "holdout_metrics": None,
        "model_input_prefix": "query: ",
    }
    (model_dir / "faqvec_v2_manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FAQVec-TR v0.2 candidate saved:", model_dir)
    print("Independent performance evaluation: NOT RUN, commercial acceptance: HOLD")


if __name__ == "__main__":
    train()
