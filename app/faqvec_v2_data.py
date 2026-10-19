"""FAQVec-TR v0.2: veri hakları, sabit niyet bölmesi ve sızıntı kontrolleri."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from app.matching import normalize
from app.database import DATA_PATH, V13_DATA_PATH

ALLOWED_LICENSES = {"OWNED", "CC0-1.0"}
ALLOWED_ORIGINS = {"OWNED": "self_authored", "CC0-1.0": "verified_cc0"}
SPLITS = ("train", "validation", "test")


class DatasetError(ValueError):
    pass


def split_intent(intent_id, seed="faqvec-v2-split-2026-10"):
    num = int.from_bytes(hashlib.sha256(
        f"{seed}:{intent_id}".encode("utf-8")
    ).digest()[:8], "big") % 100
    return "train" if num < 70 else "validation" if num < 85 else "test"


def load_bundled_demo(seed="faqvec-v2-split-2026-10"):
    """Demo etiketleri doğrulanmamıştır; ticari kullanım için otomatik izin verilmez."""
    rows = []
    for path in (DATA_PATH, V13_DATA_PATH):
        records = json.loads(path.read_text(encoding="utf-8"))
        for index, faq in enumerate(records):
            intent_id = f"{path.stem}-{index:04d}"
            rows.append({
                "intent_id": intent_id, "split": split_intent(intent_id, seed),
                "question": faq["question"],
                "alternatives": faq.get("alternative_questions", []),
                "source_id": "faqbot-bundled-demo",
                "rights_verified": False,
            })
    return rows


def _read_jsonl(path):
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"JSONL satırı {number} okunamadı.") from exc
        if not isinstance(obj, dict):
            raise DatasetError(f"JSONL satırı {number} nesne olmalı.")
        rows.append(obj)
    return rows


def load_approved_sources(manifest_path, for_commercial=False):
    """Manifest kullanıcı denetimi gerektirir, hiçbir ağ isteği başlatmaz."""
    path = Path(manifest_path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise DatasetError("Veri manifesti şema sürümü 1 olmalı.")
    sources, entries = manifest.get("sources"), manifest.get("files")
    if not isinstance(sources, list) or not isinstance(entries, list):
        raise DatasetError("sources ve files listeleri gerekli.")
    index = {}
    for source in sources:
        if not all(source.get(k) for k in ("id", "origin_url", "license_spdx", "reviewed_by")):
            raise DatasetError("Kaynak kökeni/lisansı/incelemeci eksik.")
        # Önce eski D01/D02 kaynağını her kullanım türünde reddet.
        if (
            source["id"] == "turkish-paraphrase-candidate"
            or "dogukanvzr/ml-paraphrase-tr" in source["origin_url"].lower()
        ):
            raise DatasetError(
                "D02 kullanımdan kaldırıldı: üçüncü taraf veri kaynağı "
                "kullanıcı veri politikası gereği YASAK."
            )
        if source["license_spdx"] not in ALLOWED_LICENSES:
            raise DatasetError(
                "Yalnız kendi özgün verimiz (OWNED) veya doğrulanmış CC0 kabul edilir: "
                + str(source["id"])
            )
        if source.get("origin_kind") != ALLOWED_ORIGINS[source["license_spdx"]]:
            raise DatasetError("Verinin gerçek köken türü eksik veya lisansla uyuşmuyor.")
        if source.get("rights_review_complete") is not True:
            raise DatasetError("Veri hakkı ve özgün köken incelemesi belgelenmemiş.")
        proof_name = source.get("rights_evidence_path")
        if not isinstance(proof_name, str) or not proof_name:
            raise DatasetError("Özgün üretim / CC0 kanıt dosyası gerekli.")
        proof_rel = Path(proof_name)
        if proof_rel.is_absolute() or ".." in proof_rel.parts:
            raise DatasetError("Kanıt dosyası manifest dışına çıkamaz.")
        proof = (path.parent / proof_rel).resolve()
        if not proof.is_relative_to(path.parent) or not proof.is_file():
            raise DatasetError("Kanıt dosyası yerel manifest dizininde bulunamadı.")
        if hashlib.sha256(proof.read_bytes()).hexdigest() != source.get("evidence_sha256"):
            raise DatasetError("Özgün üretim / CC0 kanıt dosyası SHA-256 uyuşmuyor.")

            raise DatasetError(f"İzin verilenler dışı/verifiye edilmemiş lisans: {source['id']}")
        if for_commercial and not source.get("commercial_training_approved", False):
            raise DatasetError(f"Ticari veri kullanımı onaylanmamış: {source['id']}")
        index[source["id"]] = source
    rows = []
    for entry in entries:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise DatasetError("Manifest dışına çıkan dosya yolu yasak.")
        target = (path.parent / relative).resolve()
        if not target.is_relative_to(path.parent):
            raise DatasetError("Manifest klasörü dışına erişim engellendi.")
        blob = target.read_bytes()
        if hashlib.sha256(blob).hexdigest() != entry.get("sha256"):
            raise DatasetError("Eğitim dosyası SHA-256 eşleşmedi.")
        for row in _read_jsonl(target):
            if row.get("source_id") not in index:
                raise DatasetError("Veride kayıtlı olmayan kaynak kimliği var.")
            rows.append(row)
    validate_intents(rows)
    return rows, manifest


def validate_intents(records):
    """Bir niyet hiçbir şekilde train ve test/validation'a bölünemez."""
    if not records:
        raise DatasetError("Boş veri kümesi.")
    intent_splits = {}
    texts = {}
    for row in records:
        intent = row.get("intent_id")
        split = row.get("split")
        if not intent or split not in SPLITS:
            raise DatasetError("intent_id ve split zorunlu.")
        if intent in intent_splits and intent_splits[intent] != split:
            raise DatasetError("Aynı niyet iki farklı veri bölmesinde!")
        intent_splits[intent] = split
        group = [row.get("question"), *row.get("alternatives", [])]
        if not all(isinstance(item, str) and item.strip() for item in group):
            raise DatasetError("Boş veya eksik soru bulundu.")
        for value in group:
            key = normalize(value)
            if not key:
                raise DatasetError("Boş normalleştirilmiş soru.")
            other = texts.get(key)
            if other and other != intent:
                raise DatasetError("İki farklı niyet aynı ifadeyi içeriyor; etiketleri kontrol edin.")
            texts[key] = intent
    return {kind: sum(s == kind for s in intent_splits.values()) for kind in SPLITS}


def positive_pairs(records, split="train"):
    """Niyet başına en fazla bir çift; in-batch yanlış negatif riskini azaltır."""
    grouped = defaultdict(list)
    for row in records:
        if row["split"] != split:
            continue
        grouped[row["intent_id"]].append(row)
    pairs = []
    for intent, group in sorted(grouped.items()):
        record = group[0]
        alts = record["alternatives"]
        if alts:
            pairs.append({"anchor": record["question"], "positive": alts[0],
                          "intent_id": intent})
    return pairs


def approved_triplets(negative_path, records):
    """Yalnızca insan tarafından onaylanmış zor negatifler eğitimde kullanılır."""
    if not negative_path:
        return []
    intents = {r["intent_id"]: r for r in records if r["split"] == "train"}
    triplets = []
    for item in _read_jsonl(negative_path):
        if item.get("status") != "approved" or not item.get("reviewed_by"):
            continue
        source, negative = item.get("anchor_intent"), item.get("negative_intent")
        if source not in intents or negative not in intents or source == negative:
            raise DatasetError("Zor negatif train bölmesinde iki ayrı niyet olmalı.")
        triplets.append({
            "anchor": intents[source]["question"],
            "positive": intents[source]["alternatives"][0],
            "negative": intents[negative]["question"],
        })
    return triplets


def write_candidate_negatives(records, outfile, top_k=3):
    """TF-IDF aday üretir, ASLA onaylandı demez."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    train = [r for r in records if r["split"] == "train"]
    matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5)).fit_transform(
        [r["question"] for r in train]
    )
    scores = cosine_similarity(matrix)
    candidates = []
    for i, row in enumerate(train):
        rank = sorted(
            (j for j in range(len(train)) if j != i and
             train[j]["intent_id"] != row["intent_id"]),
            key=lambda j: -scores[i, j]
        )[:top_k]
        for j in rank:
            candidates.append({
                "anchor_intent": row["intent_id"],
                "negative_intent": train[j]["intent_id"],
                "anchor": row["question"], "candidate_negative": train[j]["question"],
                "lexical_score": round(float(scores[i, j]), 4),
                "status": "needs_human_review",
                "reviewed_by": None,
            })
    target = Path(outfile)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in candidates),
        encoding="utf-8"
    )
    return len(candidates)
