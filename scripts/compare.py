"""2. günkü birebir eşleştirme ile 3. gün TF-IDF yöntemini karşılaştır."""

from app.database import init_db, load_faqs
from app.matching import exact_match, find_best_match

QUESTIONS = [
    "Kargom ne zaman gelir?",
    "Kargom kaç günde elime ulaşır?",
    "Ürünü geri göndermek istiyorum.",
    "Taksitle alışveriş yapabilir miyim?",
    "Nebula kuasar teleskop astronomi",
]


def main():
    init_db()
    faqs = load_faqs()
    for question in QUESTIONS:
        old = exact_match(question, faqs)
        new = find_best_match(question, faqs)
        old_category = old["category"] if old else "eşleşme yok"
        new_category = new["faq"]["category"] if new else "fallback"
        score = new["match_score"] if new else 0.0
        print(f"Soru: {question}")
        print(f"  Önceki (exact): {old_category}")
        print(f"  TF-IDF + exact: {new_category} (skor={score:.4f})")
        print()


if __name__ == "__main__":
    main()
