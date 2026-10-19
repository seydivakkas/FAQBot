# FAQVec-TR D04 — Gerçek E5 İnce Ayarı ve Model Yarışı

## Veri ve kabul sözleşmesi

Bu çalışmada üçüncü taraf Türkçe soru çiftleri veya eğitim korpusları kullanılmadı. Veri, kendi projemiz için oluşturulmuş D03-02 yapay zekâ inceleme kayıtlarıdır. Kaynak dosyalar ve kararlar: seed/faqvec_tr_ozgun_taslak_v01.json, seed/faqvec_tr_yanitsiz_taslak_v01.json ve scripts/faqvec_d03_ai_review.py.

96 niyetin 74'ü eğitim, 10'u doğrulama, 12'si test bölümünde. Galeri 96 kanonik soru içerir. Validation 20 pozitif + 11 no-answer, test 24 pozitif + 11 no-answer sorgudan oluşur. Sorular kurgusal ve AI etiketli olduğundan bu bağımsız gerçek müşteri testi değildir.

## Model ağırlıkları ve lisans

| Model | Kaynak | Yayınlanan lisans |
| --- | --- | --- |
| TF-IDF | scikit-learn yerel algoritma | Harici ağırlık yok |
| E5-base | https://huggingface.co/intfloat/multilingual-e5-base | MIT |
| FAQVec-TR | Yerel E5-base türevi araştırma fine-tune | MIT kökenli; dağıtım koşulları ayrı incelenmeli |
| Multilingual MiniLM | https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | Apache-2.0 |
| BGE-M3 | https://huggingface.co/BAAI/bge-m3 | MIT |

BGE-M3 modelinin güncel main dalında güvenli safetensors dosyası yoktur. Bu yüzden b28ce2a6fcc9c75ef1c0619575d0ec19af760082 tarihî revizyonundaki model.safetensors dosyası sabitlenir. Aynı resmî model deposunun güncel MIT lisans kartı ayrı kontrol edilir. Her model için sabit ağırlık revizyonu, SHA-256 ve lisans beyanı indirmenin yanında kaydedilir. Pickle biçimindeki pytorch_model.bin indirilmez. Model ağırlıklarını almak üçüncü taraf veri korpusu indirmek değildir.

## Gerçekleştirilen ilk deney ve devam koşusu

GitHub Actions ilk deneyinde gerçek E5-base modeli d128750597153bb5987e10b1c3493a34e5a4502a revizyonundan alındı. 74 projeye ait train çiftiyle 1 epoch / 37 adım, yaklaşık 29,89 saniye fine-tune yapıldı; eğitim loss 0,21086284. Bu kayıp test performansı değildir. İlk koşu BGE ağırlık formatında, ikinci koşu tarihî revizyonun eksik lisans alanında güvenli şekilde durdu; üçüncü koşuda aynı resmî deponun güncel MIT kartı ayrıca denetlenerek güvenli tarihi BGE ağırlığı yüklenmeye çalışılıyor.

GitHub Actions iş akışı: https://github.com/seydivakkas/FAQBot/actions/workflows/faqvec-d04-real-models.yml

TF-IDF ilk gerçek ölçüm: Recall@1 eşik öncesi 0,2083, yanlış eşleşme oranı eşik sonrası 0, cevap yok örneklerinde doğru reddetme 1,0. Bu sonuç yalnız 24 pozitif / 11 cevap yok sentetik test sorusu üzerindedir. Yanlış cevap oranının sıfır olması modelin yeterince cevap verdiğini göstermez; pozitif abstention ve genel başarı birlikte raporlanmalı.

## Ortak benchmark yöntemi

- Galeri her modelde aynı 96 kanonik soru; model yalnız train bölmesindeki 74 niyette fine-tune edilir.
- E5 soru-soru karşılaştırmasında query: öneki hem sorgu hem galeri için kullanılır. MiniLM ve BGE dense embedding öneksizdir.
- Eşik yalnız validation grubunun yanlış cevap, cevap yok ve pozitif gereksiz yanıtsızlık cezalarıyla seçilir.
- Testte Recall@1/5 (eşik öncesi), yanlış eşleşme (eşik sonrası), no-answer doğru reddetme, false answer ve pozitif abstention ayrı raporlanır.
- Eşleştirilmiş top-1 Recall farkı yalnız 12 test niyetiyle ve niyet bazlı bootstrap ile ölçülür; küçük örneklem kesin üstünlük iddiası sağlamaz.
- Model yükleme süresi, toplu sorgu süresi, tek sorgu p50/p95, RSS, varsa CUDA belleği ve yerel dosya boyutu kaydedilir. Bunlar makineye özgüdür.
- Model ağırlığı bulunmazsa benchmark skor uydurmaz ve hata verir. Yalnız gerçekten çalışan modeller rapora girer.

## Windows 11 + RTX 4070: tek PowerShell betiği

İlk kez bağımlılık, yalnız açık kaynak model ağırlığı indirme, kendi veriyle eğitim ve benchmark:

    powershell -ExecutionPolicy Bypass -File .\run_faqvec_d04_windows.ps1 -InstallDependencies -DownloadModels -Train -Benchmark

GPU doğrulama:

    .venv\Scripts\python.exe -c "import torch; print('CUDA',torch.cuda.is_available()); print('GPU',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

Model ağırlıkları bir kez indirildikten sonra benchmark internet kapalıyken yapılabilir:

    powershell -ExecutionPolicy Bypass -File .\run_faqvec_d04_windows.ps1 -Benchmark

Model çıktısı zaten varsa aynı dizin üzerine yeniden eğitim yapılmaz; yeni sürüm için benzersiz çıktı yolu kullanılmalı. PyTorch CUDA sürümü ilk kurulumda yerel NVIDIA sürücüsüyle uyumlu olmalıdır. Depodaki PowerShell betiği GPU kurulumunu kendiliğinden garanti etmez.

## Kesin kabul sınırı

AI'nın kendi yazdığı soruları yine AI ile gözden geçirmesi bağımsız gerçek müşteri testi değildir. Ticari yayın için özgün veri hakları, NOTICE/SBOM, gerçek saha verisiyle bağımsız sonuçlar, yanlış cevap güvenliği ve fiziksel Windows kabulü ayrıca doğrulanır. Model yarışı teknik araştırmadır; ticari kabul HOLD.

## Tamamlanan beş model yarışı — gerçek ölçüm

**Kanıt:** https://github.com/seydivakkas/FAQBot/actions/runs/39193432598

Bu ölçüm 19 Ekim 2026 tarihinde Ubuntu GitHub Actions CPU üzerinde gerçek model ağırlıklarıyla yapıldı. **Gerçek Windows RTX 4070 kabulü değildir.** Aynı 96 kanonik galeri kullanıldı; validation 20 pozitif+11 OOS; test 24 pozitif+11 OOS. Eşikler yalnız validation'da ayarlandı.

| Model | Eşik | Recall@1 (eşik öncesi) | Yanlış eşleşme | Pozitif abstention | OOS doğruluğu | Genel doğruluk | CPU p95* | RAM RSS** | Yerel dosya |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TF-IDF | 0,99 | %20,83 | %0,00 | %100,00 | %100,00 | %31,43 | 0,62 ms | 185,9 MB | — |
| E5-base | 0,90 | %58,33 | %16,67 | %54,17 | %90,91 | %48,57 | 68,81 ms | 1.606 MB | 1,13 GB |
| FAQVec-TR | 0,83 | %70,83 | %4,17 | %70,83 | %90,91 | %45,71 | 68,98 ms | 1.608 MB | 1,13 GB |
| MiniLM | 0,68 | %33,33 | %20,83 | %62,50 | %100,00 | %42,86 | 21,41 ms | 1.232 MB | 0,50 GB |
| BGE-M3 | 0,76 | %87,50 | %8,33 | %16,67 | %90,91 | %80,00 | 221,58 ms | 2.566 MB | 2,29 GB |

(*) Tek sorgu p95 **yalnız 6 zamanlama örneğinden** hesaplanmış ön göstergedir, kararlı performans SLA'sı değildir. (**) RSS, ilgili model işlendiğinde görülen işlem belleği olup izole model tepe RAM'i değildir. Dosya boyutu model klasörünün toplamıdır.

**Ölçülen koşu:** Python 3.12.15, Linux x86_64, inference batch_size=8, CPU. GPU kullanılmadı. BGE revizyonu b28ce2a6fcc9c75ef1c0619575d0ec19af760082; E5 revizyonu d128750597153bb5987e10b1c3493a34e5a4502a; MiniLM revizyonu e8f8c211226b894fcb81acc59f3b34ba3efd5f42.

### Mühendislik yorumu

- FAQVec-TR, E5-base'in Recall@1 değerini %58,33'ten %70,83'e (+12,50 yüzde puan) çıkardı ve yanlış cevap oranını düşürdü.
- Ancak FAQVec-TR kalibre eşikte **17/24 pozitif soruyu yanıtsız bıraktı**, genel doğruluğu %45,71 oldu. E5-base toplam doğruluğu %48,57 idi. Sadece Recall@1'e dayanarak FAQVec'in net üstünlüğü ilan edilemez.
- BGE-M3, genel doğruluk (%80,00) ve düşük pozitif abstention (%16,67) ile ilk araştırma deneyinin pratik lideri; CPU p95 sorgu süresi (221,58 ms) FAQVec'den (68,98 ms) yüksek. Model dosyası ve RAM yükü de daha büyük.
- TF-IDF yanlış cevap vermedi çünkü **24/24 pozitif sorguyu reddetti**. Bu yüzden sıfır yanlış eşleşme güvenilir ürün başarısı anlamına gelmez.
- Her test yalnız 12 niyetin 24 alternatifinden ve 11 AI-denetimli OOS örneğinden oluşuyor. Aynı kurgusal veri üretim yaklaşımından gelen kayıtlar gerçek müşteri genellemesini göstermez.
- 12 niyetle yapılan TF-IDF'ye karşı bootstrap delta: FAQVec-TR +0,50 (95% CI [0,2083; 0,7917]); BGE-M3 +0,6667 (95% CI [0,4583; 0,875]). Bu aralıklar **yalnız bu küçük sentetik niyet setinin yeniden örneklemesi** olup ticari/popülasyon üstünlüğü anlamına gelmez. FAQVec–E5 ve FAQVec–BGE için eşleştirilmiş bağımsız anlamlılık henüz raporlanmadı.

**Kesin D04 durumu:** GERÇEK_E5_EĞİTİMİ_PASS / 5_MODEL_ÖLÇÜMÜ_PASS / FAQVEC_E5_ÜZERİ_REC_AT_1_ADAY_FAYDA / BGE_PRATİK_LİDER / BAĞIMSIZ_MÜŞTERİ_BENCHMARK_HOLD / WIN_GPU_KABUL_HOLD / TİCARİ_YAYIN_HOLD.

GitHub Actions artifact adı: faqvec-d04-research-metrics-only. Altı kaynak dosya içerir: tüm model ölçüm JSON'u, TF-IDF ölçümü, eğitilmiş E5 eğitim manifesti ve üç başlangıç modelinin SHA/lisans köken kayıtları. Gerçek model ağırlıkları artifact içinde yoktur.
