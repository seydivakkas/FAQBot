# FAQBot — Hatalı Eşleşme İnceleme ve Model Karşılaştırması

## Amaç

Chatbotun gerçek soru karşısında seçtiği kaydı, yanıtı, skoru ve yöntemi incelemek; insan etiketiyle doğru hedefi belirleyip TF-IDF ve isteğe bağlı yerel embedding modeliyle güncel tahminleri kıyaslamak.

## Veri akışı

1. Yönetici Ayarlar panelinden kayıt tutmayı açar. Başlangıç ayarı kapalıdır.
2. Yalnızca loopback üzerinden yapılan yeni POST /chat isteklerinin soru ve cevap anlık görüntüsü SQLite `chat_match_reviews` tablosuna kaydedilir.
3. Her satırda zaman, soru, eşleşen SSS ID'si, eşleşen ana soru, yanıt, `match_method` ve 0–1 ölçeğindeki `match_score` tutulur.
4. Yönetici bekleyen satırı Doğru, Yanlış veya Kararsız olarak etiketler. Yanlış seçildiyse beklenen SSS kaydı ya da hiçbir cevabın verilmemesi (`null`) belirtilir.
5. Yalnızca Doğru/Yanlış etiketli kayıtlar güncel `faqs` veritabanında yeniden tahmin edilir. Silinmiş hedeflere ilişkin kayıtlar metrikten çıkarılır.

## Gizlilik

- Log tutmak açık kullanıcı/yönetici tercihi gerektirir; varsayılan kapalı.
- IP, token, çerez, cihaz bilgisi veya harici analitik SDK kullanılmaz.
- E-posta, URL, uzun sayı, bazı parola/OTP kalıplarındaki mesajlar hiç kaydedilmez. Bu sezgisel filtredir, tam kişisel veri temizliği garanti etmez.
- Yerel kayıtların son 1.000 tanesi tutulur; istenirse tüm günlük iki kez onay alarak silinir.
- API'ler localhost ile sınırlandırılır. Bu bir çok kullanıcı kimlik doğrulama sistemi değildir.

## Metrik tanımı

İnsan tarafından belirlenen `expected_faq_id`, doğru davranışın SSS kimliğidir; `null`, cevap verilmemesi gerektiğini ifade eder. Tahmin edilen SSS kimliğiyle eşitse doğru kabul edilir. `accuracy = doğru / karşılaştırılan`. Metrik bir kayıttaki cevabın güncelliği ya da içerik kalitesini kendi başına doğrulamaz.

- TF-IDF: mevcut sohbet motoru, karakter n-gram, eşik 0.40.
- Embedding: yalnızca yerel model kurulmuşsa çok dilli cümle vektörleri, eşik 0.70.
- Her iki yöntemde kayıtlı soru/alternatiflerle birebir eşleşme varsa aynı kesin eşleşme davranışı uygulanır.
- Güncel bilgi tabanıyla yeniden hesaplandığından, geçmişteki algoritma/SSS sürümüyle birebir aynı sonuç garantisi yoktur.
- Eşikler karşılaştırma için kalibrasyon gerektirir. Skorlar aynı anlama gelme olasılığı değildir.
- Kendi SSS içeriklerinden türetilen tekrar soruları bağımsız test sayılmaz; gerçek veri kabulü ileriki aşamadır.

## API

| Yöntem | Adres | İşlev |
| --- | --- | --- |
| GET/PUT | /reviews/settings | Günlük kaydı açık mı? |
| GET | /reviews | Durum filtresiyle en yeni 100 kayıt |
| PATCH | /reviews/{id} | İnsan etiketi ve beklenen SSS |
| POST | /reviews/evaluate | TF-IDF ve isteğe bağlı yerel embedding metrikleri |
| DELETE | /reviews | `confirm=true` ile tüm günlüğü temizleme |

## Sınırlar

Gerçek kişisel veri toplama ve gerçek müşteri sorularıyla algoritma kıyaslaması bu geliştirme paketinde yapılmadı. Kayıtlar uygulama kurulduğu andan itibaren değil, yönetici açıkça etkinleştirdikten sonra tutulur.
