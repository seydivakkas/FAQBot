# FAQVec-TR v0.1 — Sıfırdan eğitilen yerel soru embedding modeli

## Ticari karar

FAQVec-TR, herhangi bir önceden eğitilmiş üçüncü taraf model ağırlığına ihtiyaç duymadan mevcut FAQBot soru verisinden yerel olarak eğitilir. Ticari ürün kabulü şimdilik **HOLD**. Bunun sebebi model lisans engeli değil, kalite ve eğitim verisi haklarının henüz tam doğrulanmamasıdır.

Eski paraphrase-multilingual-MiniLM-L12-v2 modeli Apache-2.0 ile ticari kullanıma izin verir. Kendi modelimizden beklenti; ağırlık kökenini, çevrimdışı yeniden eğitimi ve sürümü denetlemektir. Bu, modelin daha iyi sonuç verdiği anlamına gelmez.

## Model

| Özellik | Değer |
| --- | --- |
| İsim | FAQVec-TR v0.1 |
| Vektör uzunluğu | 48 |
| Encoder | Türkçe normalizasyonu, kelime ve karakter 2–4 n-gram, BLAKE2b hash |
| Parametre | 4096 x 48 öğrenilebilir embedding tablosu |
| Vektör | Öğrenilmiş n-gram ortalaması + L2 normalizasyonu |
| Eğitim | Denetimli kontrastif çiftler; aynı SSS'nin ifade biçimleri pozitif |
| Negatifler | Bir batch içindeki farklı SSS ihtiyaçları |
| Kayıp | InfoNCE, sıcaklık 0.18 |
| Optimizer | NumPy ile saf Adam, LR 0.002 |
| Başlangıç | Seed 42 rastgele ağırlıklar, hiç pretrained veri kullanılmaz |
| Model formatı | weights.npz (pickle kapalı) + manifest.json (SHA-256) |
| Veriler | data/faqs.json + data/faqs_v13_additions.json; 110 kurgu SSS |

Bu model bir Transformer değildir. Genel Türkçe anlam bilgisini sıfırdan öğrenmek için 110 niyet yetersizdir. Özellikle farklı sözcüklerle sorulan aynı anlamı kaçırabilir. Yüksek doğruluk garantisi verilmez.

## Windows'ta eğitim

1. FAQBot'un normal setup_windows.bat dosyasını çalıştırın.
2. Proje klasöründeki setup_faqvec_windows.bat dosyasını açın. İkinci BAT dosyası internete bağlanmadan eğitim yapar.
3. Eğitim bitince models/faqvec-tr-v0.1/weights.npz ve manifest.json dosyaları oluşur. models/ klasörü Git'e gönderilmez.
4. Ayarlar > Benzer Sorular > FAQVec-TR — kendi eğittiğimiz yerel model > Yöntemi kaydet.
5. Benzerleri tara ve birleştirme adaylarını elle kontrol et. Sohbet cevap eşleştirme motoru halen TF-IDF'dir.

Komut: .venv\Scripts\python.exe -m scripts.train_faqvec_tr --epochs 30

## Değerlendirme ve kabul

Eğitim betiği niyetleri sabit seed ile yaklaşık %80 eğitim, %20 tutulmuş gruba böler. Tutulmuş grubun ana ve alternatif soruları üzerinden Recall@1 ölçer; karakter TF-IDF ile aynı görevde karşılaştırır. Değerlendirmeden SONRA dağıtım modeli tüm SSS'lerle yeniden eğitilir; dolayısıyla holdout rakamı dağıtım modeline ait bağımsız test değildir.

İlk iki epoch'luk CI ölçümünde FAQVec-TR Recall@1 = %33,3; karakter TF-IDF = %64,4 bulundu. Bu sayılar sadece demo verisi üzerinde ve eksik eğitim süresinde ölçülmüştür, müşteri doğruluğu değildir. İyileştirme ve eşik kalibrasyonu gerekiyor.

## Lisans ve ticarileştirme kontrolü

- Model ağırlıkları sıfırdan üretilir; eski MiniLM ağırlıkları modelin hiçbir yerinde kullanılmaz.
- Eğitim cümlelerinin ticari kullanım hakları ayrıca incelenmeli. Sentetik/demonstrasyon veri, otomatik olarak lisans temizliği sağlamaz.
- NumPy ve scikit-learn ana lisansları BSD-3-Clause'dur; ticari kullanımda telif ve lisans bildirimi dağıtımla birlikte sağlanmalıdır. Kurulu wheel ve transitive bileşenler ayrıca SBOM/NOTICE incelemesine tabidir.
- GitHub deposunun henüz bir LICENSE beyanı bulunmuyor. Bunun nasıl lisanslanacağı kullanıcı tarafından kararlaştırılmalıdır; bu belge otomatik lisans vermiyor.
- Çalışma sırasında sohbet kayıtları eğitim için otomatik toplanmaz. Müşteri mesajlarından öğrenme ancak açık izin, veri ayrımı ve gizlilik değerlendirmesi ile yapılmalı.
- Model dosyasındaki SHA-256 ağırlık bozulmalarını yakalar; kriptografik kod imzası değildir.
- Ürün PASS için hakları doğrulanmış ve bağımsız insan etiketli Türkçe müşteri verisi, başarısız soru analizi, offline Windows kabulü, performans sınırları ve lisans denetimi gerekli.

Bu teknik ve ticari kabul taslağı hukuki mütalaa değildir.