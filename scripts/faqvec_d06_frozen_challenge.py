"""FAQVec D06: sıfırdan yazılmış ve mühürlenmiş *yalnız test* Türkçe zor sorular.

Bu dosyadaki hiçbir örnek eğitim/validation/eşik ayarında kullanılmaz.
Kaynak doğruluğu AI etiketidir; müşteri/bağımsız insan testi değildir.
"""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.matching import normalize
from app.faqvec_v2_data import DatasetError
from scripts.faqvec_d03_ai_review import evaluate
from scripts.faqvec_d05_owned_data import load_auxiliary_training

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_PATH = ROOT / "seed" / "faqvec_d06_yeni_ozgun_zor_test_v01.json"
FROZEN_GIT_BLOB = "47ed47c00edfc2bf8ae19816f9949622bc8582f8"
SOURCE_ID = "faqvec-d06-own-written-eval"


def git_blob_sha(path=CHALLENGE_PATH):
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def frozen_challenge():
    if git_blob_sha() != FROZEN_GIT_BLOB:
        raise DatasetError("D06 test dosyası dondurulmuş kaynaktan farklı; sonuç kabul edilmez.")
    data = json.loads(CHALLENGE_PATH.read_text(encoding="utf-8"))
    if (data.get("schema_version") != 1
        or data.get("source_id") != SOURCE_ID
        or data.get("origin_kind") != "project_authored_ai_draft"
        or data.get("role") != "test_only_frozen_do_not_tune"
        or data.get("split") != "new_challenge_test_never_validation_or_train"
        or data.get("commercial_training_approved") is not False
        or data.get("rights_review_complete") is not False
        or data.get("independent_customer_sample") is not False
        or data.get("independent_human_review") is not False):
        raise DatasetError("D06 yalnız kendi AI taslağı TEST verisi olmalı; ticari onay yasak.")
    records = data.get("records")
    if not isinstance(records, list) or len(records) != 72:
        raise DatasetError("D06 sabit 72 soru sözleşmesi bozuldu.")

    old, *_ = evaluate()
    known = {r["intent_id"]: r for r in old}
    old_questions = {
        normalize(q)
        for r in old for q in (r["question"], *r["alternatives"])
    }
    new_train = load_auxiliary_training()
    old_questions.update(
        normalize(q)
        for r in new_train for q in (r["question"], *r["alternatives"])
    )
    ids = set()
    normalized = set()
    counts = defaultdict(Counter)
    positives = []
    oos = []
    for r in records:
        ident = r.get("case_id")
        domain = r.get("domain")
        question = r.get("query")
        label = r.get("expected_intent_id", "__MISSING__")
        if (not isinstance(ident, str) or not ident.startswith("d06-")
            or ident in ids or not isinstance(domain, str)
            or not isinstance(question, str) or not question.strip()
            or len(question) > 400):
            raise DatasetError("D06 kaynakta eksik/tekrar/bozuk soru.")
        ids.add(ident)
        key = normalize(question)
        if not key or key in normalized or key in old_questions:
            raise DatasetError("D06 sorusu D03/D05 eğitim/validation/test ile çakışıyor.")
        normalized.add(key)
        if (r.get("source_id") != SOURCE_ID
            or r.get("human_review") != "not_performed"
            or r.get("ai_authored") is not True):
            raise DatasetError("D06 testte insan onayı veya harici veri kaynağı iddiası var.")
        if r.get("kind") == "positive":
            if label not in known or known[label]["domain"] != domain:
                raise DatasetError("Pozitif soru kendi galerisinde yanlış niyete bağlanmış.")
            if "confusable_with" in r:
                raise DatasetError("Pozitif soruda OOS karşıt niyeti olamaz.")
            positives.append(r)
        elif r.get("kind") == "near_miss_out_of_scope":
            if label is not None:
                raise DatasetError("Yakın OOS sorusunun gerçek niyet etiketi bulunamaz.")
            negative_id = r.get("confusable_with")
            if negative_id not in known or known[negative_id]["domain"] != domain:
                raise DatasetError("OOS karşıt niyeti galeri alanıyla uyuşmuyor.")
            oos.append(r)
        else:
            raise DatasetError("D06 test sorgusu kategorisi geçersiz.")
        counts[domain][r["kind"]] += 1
    if len(positives) != 48 or len(oos) != 24 or len(counts) != 12:
        raise DatasetError("D06 48 pozitif / 24 yakın OOS / 12 alan kuralı bozuldu.")
    for domain, c in counts.items():
        if c["positive"] != 4 or c["near_miss_out_of_scope"] != 2:
            raise DatasetError(f"{domain} D06 alanındaki 4+2 sınaması değişmiş.")
    return records


def challenge_queries():
    records = frozen_challenge()
    return [
        {"query": item["query"], "expected_id": item["expected_intent_id"],
         "source": "d06_project_ai_authored_frozen_hard_test",
         "case_id": item["case_id"],
         "domain": item["domain"],
         "kind": item["kind"],
         "confusable_with": item.get("confusable_with")}
        for item in records
    ]


def summary():
    queries = challenge_queries()
    old, *_ = evaluate()
    mapping = {x["intent_id"]: x["split"] for x in old}
    positive_by_old_split = Counter(
        mapping[x["expected_id"]] for x in queries
        if x["expected_id"] is not None
    )
    return {
        "frozen_git_blob": FROZEN_GIT_BLOB,
        "total": len(queries), "positive": sum(x["expected_id"] is not None for x in queries),
        "near_miss_oos": sum(x["expected_id"] is None for x in queries),
        "domains": len(set(x["domain"] for x in queries)),
        "positive_by_D03_intent_split": dict(sorted(positive_by_old_split.items())),
        "existing_gallery_unchanged": 96,
        "no_training_or_validation_use": True,
        "human_labels": False,
        "independent_customer_test": False,
        "commercial_acceptance": "HOLD"
    }


if __name__ == "__main__":
    print("D06_FROZEN_CHALLENGE=" + json.dumps(summary(), ensure_ascii=True))
