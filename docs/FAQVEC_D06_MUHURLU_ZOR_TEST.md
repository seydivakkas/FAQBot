# FAQVec-TR D06 — Mühürlü, Sıfırdan Yazılmış Türkçe Zor Test ve Çift Güvenlik Eşiği

**Kural:** Eğitim verisi yalnız kendi özgün metinlerimiz veya kökeni doğrulanmış CC0/kamu malıdır. Üçüncü taraf soru korpusu indirilmez veya karıştırılmaz. MIT/Apache-2.0 model **ağırlıkları** ayrı lisans ve NOTICE koşullarına tabidir.

**Aşamanın odağı:** FAQVec-D05'in yanlış niyete yönelmelerini artırmadan, gerçekten doğru yanıt verilen soru sayısını yükseltmek; model ayarını sınama sorularına göre değiştirmemek.

## 1. Dondurulmuş yeni sınama kümesi

Özgün test dosyası: `seed/faqvec_d06_yeni_ozgun_zor_test_v01.json`.

- **72 yepyeni kurgusal Türkçe müşteri sorusu**, 12 alanda her biri 6 örnek.
- 48 pozitif sorgu: önceki 96 SSS galerisindeki bilinen niyetlere farklı ifadelerle yöneltilmiş sorular, alan başına 4.
- 24 yakın kapsam dışı (near-miss/OOS): galerideki benzer niyetlere yüzeysel olarak benzeyen fakat mevcut FAQ cevaplarının kapsamına girmeyen yeni talepler, alan başına 2.
- Kaynak Git blob SHA: `47ed47c00edfc2bf8ae19816f9949622bc8582f8`; dosyanın herhangi bir değişikliğinde sınama yükleyicisi hata verir.
- Test kimlikleri, hedef niyet, benzer ama yanlış niyet ve alan bilgisi saklanır. Veri kullanıcı tarafından sağlanan gerçek müşteri konuşması içermez.
- **Kesin sınır:** Bu soruları hiçbir model eğitimi, negatif örnek madenciliği, validation/eşik araması veya iyileştirme önerisi üretirken referans almıyoruz. D06 testi tüketildikten sonra sonuçlara göre ayar yapmak istersek yeni bir ayrı sınama paketi ve önceden sabitlenmiş protokol gerekecek.
- Kaynak projeye yeni yazılmış AI taslağıdır. İki bağımsız insan etiketi, gerçek müşteri toplama veya saha testi yapılmadı. `independent_customer_test=false` ve `commercial_training_approved=false` olarak tutulur.

## 2. Doğrulama ve doğru ölçüm sözleşmesi

- Galeri **D04'ten değişmeyen 96 kanonik FAQ**; D05'e eklenen 24 yardımcı niyet yalnız eğitim verisidir, galeriye/teste dahil edilmez.
- Parametre kalibrasyonunda **yalnız önceki D04 validation: 20 pozitif + 11 OOS** kullanılır.
- Yeni D06 verisi **48 pozitif + 24 yakın OOS** olarak sadece final testinde ölçülür.
- Altı model: TF-IDF, orijinal E5-base, FAQVec-D04, FAQVec-D05, MiniLM-L12-v2, BGE-M3.
- Aynı modellerde iki politikanın testi raporlanır: D05 tek maksimum benzerlik eşiği ve D06 çift kapı: `top1_score >= threshold` ve `top1_score - top2_score >= margin`.
- D06 çift kapıda eşik 201 sabit aday (0,00–1,00), marj 51 sabit aday (0,00–0,25). Seçim yalnız eski validation'da **yanlış niyet <=%10 ve OOS yanlış cevap <=%10** koşulunu sağlayanlar arasından en çok *doğru pozitif cevabı* veren çiftle yapılır. Testten hiçbir skor/etiket seçim aşamasına girmez.
- Aynı yeni testte doğru pozitif sayısı, yanlış niyet, gereksiz abstention, OOS yanlış cevap, OOS doğru reddetme, coverage, answered-risk, toplam doğruluk ve gerçek çalışma süresi ölçülür. Sonuçlar alan bazlı dört sayı ile açıklanır.
- Recall@1 **eşikten önceki** sıralama doğruluğudur. Yalnız Recall@1 yükselmesi bir ürünün daha doğru veya güvenli cevapladığı anlamına gelmez.
- Bu küçük AI-yazımı testte validation kapısı tutsa bile, D06 testte kapının mutlaka tutacağı garanti edilmez.

## 3. Değişmez mühendislik ve lisans sınırları

Projenin veri kaynak kodu `scripts/faqvec_d06_frozen_challenge.py` üzerinden Git blob ve çakışma kontrolü yapar. Model test aracı `scripts/faqvec_d06_hard_benchmark.py`; güvenlik kapısı `app/faqvec_d06_margin_gate.py`.

Model indirme yalnız açık izin verilmiş ilk bağımlılık kurulumundadır. Ağırlıklar yereldeyken test `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `trust_remote_code=False`, `local_files_only=True` ile çalışır. Herhangi bir LLM API key veya üçüncü taraf inference servisine soru aktarımı kullanılmaz.

Gerçek model yarışı ve ölçüm kanıtı: https://github.com/seydivakkas/FAQBot/actions/workflows/faqvec-d06-frozen-hard.yml . Model ağırlıkları veya test metinleri GitHub Actions artifact'ına yüklenmez; yalnız ölçüm JSON ve köken manifestleri yayınlanır.

## 4. Windows/RTX yerel son kabul yolu

Model indirmeden ve eğitim yapmadan önce yalnız sabit kaynak kontrolü:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_faqvec_d06_windows.ps1
```

Beş gerçek ağırlık klasörü ve FAQVec-D04/D05 modelleri yerel makinede hazırsa:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_faqvec_d06_windows.ps1 -Compare
```

Bu komut Windows'taki modelleri çevrimdışı değerlendirir, raporu `reports\faqvec_d06` klasörüne yeni bir JSON dosyası olarak kaydeder; üzerine yazmaz. Windows GPU, RAM, VRAM, Edge ve çevrimdışı .exe fiziksel kabulünün yapıldığını tek başına göstermez.

## 5. Ticari yayın engelleri

AI tarafından yazılan ve aynı AI tarafından kontrol edilen sorular bağımsız müşteri kalite kanıtı değildir. Üretim öncesi gerçek kullanım senaryosu, veri kökeni, model ağırlığı/NOTICE/SBOM, gizlilik ve işletmeye özgü cevap uygunluğu; son aşamada gerçek Windows/Edge kabulü gerekecek. Bu yüzden `TİCARİ_YAYIN_HOLD` değişmez.

**Geçici karar:** `D06_ÖZGÜN_72_ZOR_TEST_SABİT / TEK_VE_ÇİFT_EŞİK_KODLANDI / GERÇEK_MODEL_YARIŞI_KANIT_BEKLİYOR / BAĞIMSIZ_MÜŞTERİ_TESTİ_HOLD / TİCARİ_YAYIN_HOLD`.
