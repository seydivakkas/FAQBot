"""Özgün veri politikası: üçüncü taraf korpus indirmesi kapatılmıştır.

D01/D02 geçmiş denetim sayımları arşivde kalır, ancak bu betik dış
korpusu yeniden indirmez. Yalnız özgün kendi verimiz veya doğrulanmış
CC0/kamu malı veriler kullanılır.
"""


def main():
    raise SystemExit(
        "D01/D02 üçüncü taraf veri indirmesi kullanıcı kararıyla DEVRE DIŞI. "
        "FAQVec-TR için yalnız kendi ürettiğiniz veya doğrulanmış CC0/kamu malı veri kullanın."
    )


if __name__ == "__main__":
    main()
