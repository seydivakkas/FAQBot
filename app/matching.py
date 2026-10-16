"""Birebir eşleştirme ve TF-IDF tabanlı soru benzerliği."""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_THRESHOLD = 0.40


def normalize(text: str) -> str:
    """Türkçe I/İ farkını koruyarak noktalama ve boşlukları sadeleştir."""
    text = text.translate(str.maketrans({"I": "ı", "İ": "i"})).lower()
    return " ".join(re.findall(r"\w+", text, flags=re.UNICODE))


def exact_match(message: str, faqs: list[dict]) -> dict | None:
    """Eski yöntem: ana/alternatif sorunun birebir normalleştirilmiş hali."""
    query = normalize(message)
    for faq in faqs:
        phrases = [faq["question"], *faq.get("alternative_questions", [])]
        if any(normalize(phrase) == query for phrase in phrases):
            return faq
    return None


def find_best_match(
    message: str,
    faqs: list[dict],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict | None:
    """Önce birebir, ardından char n-gram TF-IDF ile eşleşme yap.

    Bulunan sonuç: faq, match_type ve match_score.
    Benzerlik eşiğinin altında kalan sorular için None döner.
    """
    if not normalize(message) or not faqs:
        return None

    exact = exact_match(message, faqs)
    if exact is not None:
        return {"faq": exact, "match_type": "exact", "match_score": 1.0}

    phrases = []
    owners = []
    for faq in faqs:
        for phrase in [faq["question"], *faq.get("alternative_questions", [])]:
            if normalize(phrase):
                phrases.append(normalize(phrase))
                owners.append(faq)

    if not phrases:
        return None

    # Küçük (20 soruluk) MVP'de her istek için vektörleştirme yeterince basit.
    # Daha büyük veri setinde indeks/cache ayrı değerlendirilebilir.
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        lowercase=False,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform([*phrases, normalize(message)])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    best_index = int(scores.argmax())
    score = float(scores[best_index])

    if score < threshold:
        return None

    return {
        "faq": owners[best_index],
        "match_type": "tfidf",
        "match_score": round(score, 4),
    }
