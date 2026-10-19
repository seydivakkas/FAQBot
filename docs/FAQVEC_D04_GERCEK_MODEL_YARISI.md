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
