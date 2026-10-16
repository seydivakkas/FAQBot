"""Normalizasyon, birebir ve TF-IDF soru eşleştirme testleri."""

from app.matching import exact_match, find_best_match, normalize


FAQS = [
    {
        "question": "Kargom ne zaman gelir?",
        "answer": "Kargo cevabı",
        "category": "kargo",
        "alternative_questions": ["Kargom kaç günde ulaşır?"],
    },
    {
        "question": "Ürünümü nasıl iade ederim?",
        "answer": "İade cevabı",
        "category": "iade",
        "alternative_questions": ["Ürünü geri göndermek istiyorum."],
    },
]


def test_turkish_normalization():
    assert normalize("  İADE, İŞLEMİ! ") == "iade işlemi"
    assert normalize("KARGOM???") == "kargom"


def test_exact_matches_are_normalized():
    matched = exact_match("  KARGOM NE ZAMAN GELİR??? ", FAQS)
    assert matched["category"] == "kargo"


def test_alternative_question():
    matched = find_best_match("Ürünü geri göndermek istiyorum.", FAQS)
    assert matched["faq"]["category"] == "iade"
    assert matched["match_type"] == "exact"


def test_tfidf_paraphrase():
    matched = find_best_match("Kargom kaç günde elime ulaşır?", FAQS)
    assert matched is not None
    assert matched["faq"]["category"] == "kargo"
    assert matched["match_type"] == "tfidf"


def test_unrelated_question():
    assert find_best_match("Nebula kuasar teleskop astronomi", FAQS) is None


def test_empty_data():
    assert find_best_match("Kargo", []) is None
    assert find_best_match("   ", FAQS) is None
