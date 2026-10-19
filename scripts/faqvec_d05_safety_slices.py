"""D05 OOS güvenlik dilimleri. Sabit D04 benchmark testine YENİ veri eklemez.

22 AI taslak cevap-yok sorusunu sınıflandırarak tehlikeli/gerçekdışı
sorguların hata payını genel başarı ortalamasında gizlememeyi sağlar.
Sınıflar gerçek kişisel veri içermez, müşteri gizli verisi kullanılmaz.
"""
from collections import Counter

from scripts.faqvec_d03_ai_review import evaluate
from scripts.faqvec_d04_real_benchmark import build_research_suite
from app.matching import normalize

PRIVATE = {
    "oos-siparis-1", "oos-kargo-1", "oos-odeme-1",
    "oos-uyelik-1", "oos-uyelik-2", "oos-teslimat-1",
    "oos-destek-1", "oos-fatura-1", "oos-gizlilik-1",
    "oos-gizlilik-2",
}
CONFIDENTIAL = {
    "oos-degisim-1", "oos-odeme-2", "oos-kampanya-1",
    "oos-urun-1", "oos-destek-2"
}
UNVERIFIED = {
    "oos-siparis-2", "oos-kargo-2", "oos-iade-1",
    "oos-degisim-2", "oos-fatura-2"
}
SPECIALIST = {"oos-iade-2", "oos-urun-2"}

MESSAGE = {
    "private_information": (
        "Başka kişilerin özel bilgilerini, hesap erişim bilgilerini "
        "veya ödeme sırlarını paylaşamam. Yetkili destek üzerinden "
        "kimliğinizi doğrulayarak başvuru yapabilirsiniz."
    ),
    "confidential_information": (
        "Bu iç veya doğrulanmamış bilgiyi açıklayamam. "
        "Kamuya açık, teyit edilebilir bir kaynak ya da yetkili "
        "destek açıklaması gerekiyor."
    ),
    "unverified_or_future_information": (
        "Bu bilgiye doğrulanmış erişimim yok; kesin bir sonuç "
        "veya tarih taahhüt edemem. İlgili resmî takip kanalını kullanın."
    ),
    "specialist_decision": (
        "Bu konuda bağlayıcı hukukî veya tıbbi karar veremem. "
        "Yetkili bir uzmandan değerlendirme alın."
    ),
}
CLASS_OF = {
    **{key:"private_information" for key in PRIVATE},
    **{key:"confidential_information" for key in CONFIDENTIAL},
    **{key:"unverified_or_future_information" for key in UNVERIFIED},
    **{key:"specialist_decision" for key in SPECIALIST},
}


def safety_slices():
    _rows, _review, _negative, oos, _stats = evaluate()
    included = {
        item["candidate_id"]:item
        for item in oos
        if item["ai_decision"] == "no_answer_research_candidate"
    }
    if len(included) != 22 or set(included) != set(CLASS_OF):
        raise ValueError("D05 güvenlik sınıf sözleşmesi D04 OOS kayıtlarıyla uyuşmuyor.")
    _, _, queries = build_research_suite()
    lookup = {
        normalize(row["query"]): row["candidate_id"] for row in included.values()
    }
    output=[]
    for split in ("validation","test"):
        for query in queries[split]:
            if query["expected_id"] is not None:
                continue
            ident = lookup.get(normalize(query["query"]))
            if not ident:
                raise ValueError("OOS sorgusu kaynağı bulunamadı.")
            kind = CLASS_OF[ident]
            output.append({
                "candidate_id":ident,
                "split":split,
                "risk_class":kind,
                "fallback":MESSAGE[kind],
                "source":"project_authored_ai_draft",
                "human_verified":False,
                "commercial_training_approved":False,
            })
    return output


def summary():
    rows=safety_slices()
    return {
        "total":len(rows),
        "validation":sum(x["split"]=="validation" for x in rows),
        "test":sum(x["split"]=="test" for x in rows),
        "risk_classes":dict(sorted(Counter(x["risk_class"] for x in rows).items())),
        "independent_human_review":False,
        "commercial_acceptance":"HOLD",
    }


if __name__ == "__main__":
    import json
    print("D05_SAFETY_SLICES="+json.dumps(summary(),ensure_ascii=True))
