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

## 6. Gerçek altılı model yarışının sonucu — 19 Ekim 2026

**Gerçek Linux CPU + model ağırlıkları:** [GitHub Actions D06 #39219421149](https://github.com/seydivakkas/FAQBot/actions/runs/39219421149) → **SUCCESS**. E5-base ve FAQVec-D04/D05 ağırlıkları gerçek MIT E5'ten üretildi; MiniLM Apache-2.0 ve BGE-M3 MIT model ağırlıkları karşılaştırıldı. Önceden mühürlenmiş 72 soru eğitim ve threshold seçiminde kullanılmadı.

Eski D04 validation (20 pozitif + 11 OOS) üzerinden tek koşullu D05 eşiği ile D06 benzerlik+ilk-iki-skor-farkı kapısı bağımsız olarak sabitlendi. Testte 48 cevaplanabilir yeni soru, 24 yakın OOS var.

| Model | Recall@1 (eşik öncesi) | Tek eşik doğru /72 | Çift eşik doğru /72 | Çift eşik yanlış niyet /48 | Çift eşik OOS yanlış cevap /24 | Çift eşik doğru pozitif /48 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TF-IDF | %29,17 | 27 | 27 | 0 | 0 | 3 |
| E5-base | %52,08 | 35 | 37 | 4 | 1 | 14 |
| FAQVec-D04 | %66,67 | 36 | 35 | 1 | 1 | 12 |
| **FAQVec-D05** | **%75,00** | **36** | **35** | **1** | **1** | **12** |
| MiniLM | %43,75 | 28 | 28 | 4 | 3 | 7 |
| BGE-M3 | %79,17 | 49 | 49 | 2 | 6 | 31 |

**Kilitli validation sonucunda seçilen çift kapı (benzerlik eşiği; top1–top2 marjı):** TF-IDF (0,430; 0,010), E5 (0,895; 0,005), FAQVec-D04 (0,830; 0,020), FAQVec-D05 (0,735; 0,030), MiniLM (0,685; 0,010), BGE-M3 (0,730; 0,010). Bu parametreler D06 etiketlerine bakılarak **değiştirilmedi**.

### Yanlış cevap ve kapsam dengesi

- FAQVec-D05 **yeni soruların %75'ini ilk sırada doğru buldu (36/48)**; ancak çift güvenlik kapısıyla yalnız **12/48** doğru cevap verdi, 1/48 yanlış niyetle cevap verdi ve **35/48'i cevapsız bıraktı**. Yakın OOS örneklerinin 23/24'ünü reddetti.
- Tek koşullu D05 kapısı FAQVec-D05 için **13 doğru pozitif, 1 yanlış pozitif, 34 abstention, 1 OOS false-answer** üretmişti. Çift kapı doğru yanıtı **13'ten 12'ye düşürdü**, yanlışları değiştirmedi. **Bu değişikliği FAQVec için varsayılan üretim ayarı olarak KABUL ETMİYORUZ.**
- FAQVec-D04 ile D05'in çift eşikli testteki toplam doğru karar sayısı aynı **35/72**. FAQVec-D05 top1 Recall@1 değeri +8,33 yüzde puan yükseldi, fakat bu **kullanılabilir doğru cevap** artışı değildir.
- BGE-M3, çift kapıyla **31 doğru pozitif** ve **18 doğru OOS reddi** yaptı. Yanlış pozitif niyet sayısı tek eşiğe göre 4'ten 2'ye düştü; buna karşılık **6/24 OOS yanlış cevabı** sürdü. D06 OOS %25 yanlış cevap = güvenlik koşulu FAIL. Daha yüksek toplam doğruluk, otomatik yayımlanabilirlik anlamına gelmez.
- TF-IDF sıfır yanlış cevap vermiş olsa da **45/48 pozitif soruyu reddettiği için** kullanılabilir değildir.
- E5-base çift kapıda 14 doğru pozitif, 4 yanlış pozitif ve 1 OOS false-answer verdi. Hata oranları D06 araştırma için belirlediğimiz %10 sınırının hemen altında kalır; saha garantisi değildir.

### Belirsizlik ve karşılaştırma

Yalnız bu 48 tekil kurgusal test niyeti üzerinde eşleştirilmiş Recall@1 bootstrap sonuçları: FAQVec-D05 eksi D04 = **+8,33 yüzde puan**, %95 aralık **[0; +18,75]** (sıfırı kapsıyor); FAQVec-D05 eksi E5-base = **+22,92 puan**, aralık **[+10,42; +35,42]**; FAQVec-D05 eksi BGE-M3 = **−4,17 puan**, aralık **[−16,67; +8,33]**. Bunlar yalnız AI tarafından yazılan ayrı kurgusal sorular için örnekleme tanısıdır, genel bağımsız model üstünlüğü kanıtı değildir.

**Mühendislik kararı:** `D06_72_ÖZGÜN_TEST_SHA_PASS / GERÇEK_6_MODEL_YARIŞI_PASS / FAQVEC_TOP1_İYİLEŞTİ / KULLANILABİLİR_DOĞRU_SAYISI_ARTMADI / ÇİFT_EŞİK_FAQVec_PROMOSYONU_RED / YAKIN_OOS_GÜVENLİK_HOLD / BAĞIMSIZ_SAHA_TESTİ_HOLD / TİCARİ_YAYIN_HOLD`.

## 7. Sonraki kontrollü sınır

D06 sonuçlarını yeni eğitim çiftleri veya eşikler üretmek için geri beslemiyoruz; aksi takdirde kilitli zor test artık tarafsız holdout olmayacaktır. Sıradaki araştırma veri paketi *ayrı yeni bir TRAIN/VALIDATION kaynağı* olmalı. Doğru cevap sayısını artırmayı hedefleyen yenilikler yalnız yeni validation'da denenmeli; nihai değerlendirme için daha sonra **yeni, görülmemiş** bir holdout hazırlanmalı. Gerçek müşterilerin izinli/anonim soruları bulunmadığından ticari kabul hâlâ HOLD.

D06'nın gerçek model ağırlıkları GitHub artifact'ında dağıtılmaz; rapor adı `faqvec-d06-frozen-hard-metrics-only`, içerik yalnız JSON metrikler ve ağırlık köken kayıtlarıdır.
