> **ARŞİV — BU YOL ARTIK KULLANILMAYACAK.** Kullanıcının kesin veri politikası gereği üçüncü taraf `dogukanvzr/ml-paraphrase-tr` veri kümesi indirilmeyecek, işlenmeyecek, eğitimde veya karşılaştırmada kullanılmayacak. Önceki kaynak sayımları yalnız geçmiş teknik kayıtlarıdır. Yeni çalışma: [yalnız OWNED / doğrulanmış CC0](VERI_KAYNAGI_KESIN_POLITIKA.md). Kaynak yayıncısından izin isteme planı iptal edilmiştir.

# FAQVec-TR v0.2 — Ticari Odaklı Embedding Geliştirme Sözleşmesi

## Karar

FAQVec-TR v0.1 (48 boyutlu ve sıfırdan eğitim) henüz TF-IDF'yi geçemedi: 30 epoch ayrılmış demo niyetlerinde Recall@1 %42,2; TF-IDF %64,4. FAQVec-TR v0.2, MIT lisanslı intfloat/multilingual-e5-base modelinden ince ayar yapılan TÜREV bir modeldir. Orijinal ağırlıkları kendimiz yazdık denmez.

Temel model: https://huggingface.co/intfloat/multilingual-e5-base (MIT, 768 boyut).
Rakip: https://huggingface.co/BAAI/bge-m3 (MIT, 1024 boyut).
Diğer rakip: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (Apache-2.0).

## Windows-first ve maliyet

1. Normal FAQBot kurulum dosyası setup_windows.bat ile temel sistem kurulur.
2. İsteğe bağlı setup_faqvec_v2_windows.bat ilk çalıştırmada kullanıcıdan onay alır; Python eğitim bağımlılıkları ve 1 GB üzeri olabilen E5 ağırlıkları bir kez indirilir.
3. E5 modelinin gerçek revizyon kimliği ve MIT lisans kaydı modeller/e5-base-original/faqvec_backbone_origin.json altında saklanır.
4. Eğitim ile model kullanımı yerel diskte olur; zorunlu bulut/ücretli API yoktur.
5. Demo deneyde ağırlıklar models/faqvec-tr-v0.2-e5/model dizinine kaydedilir. Üzerine yazma engellenmiştir.
6. 8 GB VRAM için batch-size 2 ve gradient-accumulation 8 başlangıç önerisidir, GPU belleğine sığma garantisi yoktur.

İsteğe bağlı işlemleri ayrı ayrı yapmak için proje kökünden:
  .venv\Scripts\python.exe -m pip install -r requirements-faqvec-v2.txt
  .venv\Scripts\python.exe -m scripts.fetch_faqvec_v2_backbone
  .venv\Scripts\python.exe -m scripts.train_faqvec_v2 --demo --epochs 2 --batch-size 2
  .venv\Scripts\python.exe -m scripts.benchmark_faqvec_v2 --demo --model e5-base=models/e5-base-original --model faqvec-v2=models/faqvec-tr-v0.2-e5/model

## Veri lisansı ve güvenlik kapısı

app/faqvec_v2_data.py içindeki kayıtlarda intent_id ve train/validation/test alanları zorunlu; niyetler bölmeler arasında sızamaz. İlk 110 demo SSS ticari eğitim izni yerine geçmez.
Haricî veri manifesti için source_id, origin_url, license_spdx, reviewed_by, evidence_sha256, commercial_training_approved ve dosya SHA-256 bilgileri gereklidir. --commercial yalnızca onaylı veriyle çalışır. Bu kontrol hukuki onay yerine geçmez.
Sadece insanın status=approved ve reviewed_by olarak işaretlediği hard negative örnekleri eğitime alınır. scripts.suggest_faqvec_v2_negatives varsayılan needs_human_review durumundaki adayları üretir.
MultipleNegativesRankingLoss ve BatchSamplers.NO_DUPLICATES kullanılır. E5 için hem sorgu hem de galeri soru ifadeleri query: önekiyle kodlanır. Yanlış negatifler ve değerlendirme verisi kaçakları ayrıca insan incelemesi ister.

## Adil benchmark

scripts/benchmark_faqvec_v2.py tüm sistemleri aynı galeride ve aynı sorgularda test eder. TF-IDF, E5-base, v0.2, BGE-M3 ve MiniLM yerel klasörlerle seçenek olarak desteklenir.
Metikler: Recall@1, Recall@5, yanlış eşleşme oranı, cevap gerekirken yanıtsız bırakma, cevap gerekmeyene yanlış cevap verme ve doğru fallback.
Her model eşiği yalnızca validation bölmesinde hem pozitif hem insan onaylı cevap-yok soruları varsa kalibre edilir. Yoksa diagnostic_only=true, gerçek reddetme başarısı iddia edilmez.
Demo örneklerinden çıkan rakam bağımsız müşteri testi değildir. Eğitimde kullanılan niyetler ve müşteri test kümesi net ayrılmalıdır.

## Ticari kabul

Bu committe E5-base ağırlıkları CI içinde indirilip GPU'da fine-tune edilmedi; gerçek büyük model performans kabulü yapılmadı. Mevcut testler hazırlama, veri sızıntısı ve ölçüm mantığını doğrular. Sonraki görev hakları doğrulanmış geniş soru çiftleri, uzman etiketli zor negatifler, açıkça yanıtsız kalması gereken sorular, BGE-M3 karşılaştırması, gecikme/VRAM testi, offline Windows paketi, SBOM ve lisans NOTICE incelemesidir.
MIT lisanslı pretrained modeli kullanmak ve ince ayar yapmak ticari kullanım bakımından uygundur ancak kaynak bildirimi ve bağımlılık lisans yükümlülükleri korunmalıdır. Ticari ürün kabulü HOLD.
