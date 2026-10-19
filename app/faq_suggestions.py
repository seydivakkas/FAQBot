"""P1: yalnız SSS önerisi; düşük skor hiçbir zaman otomatik cevaba dönüştürülmez."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.matching import normalize


def suggest_faqs(question, faqs, *, limit=3, min_score=0.16, exclude_id=None):
    if not normalize(question) or not faqs or not 1 <= limit <= 5:
        return []
    phrases, owners = [], []
    for faq in faqs:
        if faq["id"] == exclude_id:
            continue
        seen = set()
        for item in (faq["question"], *faq.get("alternative_questions", [])):
            word = normalize(item)
            if word and word not in seen:
                seen.add(word)
                phrases.append(word)
                owners.append(faq)
    if not phrases:
        return []
    model = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(2, 5), lowercase=False,
        sublinear_tf=True,
    )
    vectors = model.fit_transform([*phrases, normalize(question)])
    scores = cosine_similarity(vectors[-1], vectors[:-1]).ravel()
    ranked = {}
    for score, faq in zip(scores, owners):
        if np.isfinite(score) and score >= min_score:
            ranked[faq["id"]] = max(float(score), ranked.get(faq["id"], 0.0))
    selected = sorted(ranked.items(), key=lambda p: (-p[1], p[0]))[:limit]
    by_id = {faq["id"]:faq for faq in faqs}
    return [
        {
            "faq_id": key,
            "question": by_id[key]["question"],
            "category": by_id[key]["category"],
            "score": round(score, 4),
            "is_answer": False,
        }
        for key, score in selected
    ]
