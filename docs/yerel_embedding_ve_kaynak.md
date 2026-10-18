# FAQBot — Yerel Embedding ve Kaynak Yönetimi

## Windows modeli isteğe bağlı kurma

1. Önce setup_windows.bat ile normal FAQBot kurulumunu tamamlayın.
2. Proje klasöründeki setup_embedding_windows.bat dosyasını çift tıklayın. Ağır bağımlılıklar ve model **yalnızca bu açık komutla** indirilir; internet ilk seferde gereklidir.
3. FAQBot → Ayarlar → Benzer Soruları İncele → Yerel embedding'i seçin ve yöntemi kaydedin.
4. Varsayılan model dizini: FAQBot/models/paraphrase-multilingual-MiniLM-L12-v2

Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (çok dilli, 384 boyut, Apache-2.0).
Kaynak: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

Yerel yükleme local_files_only=True ve trust_remote_code=False ayarlarıyla yapılır. Çalışma sırasında model otomatik indirilmez; kurulum eksikse açık hata döner. Normal soru-cevap sohbeti TF-IDF motorunda kalır; embedding yalnızca benzer soru adayları içindir.

Önceden kaydedilen yüzde benzerlik eşiği her iki yöntemin aday filtrelemesinde kullanılır. Embedding ve TF-IDF skorları aynı istatistiksel anlama gelmez; bir skor aynı anlamın olasılığı değildir.

## Kaynak ve doğrulama sözleşmesi

Her SSS kaydına kaynak başlığı, http/https kaynak URL'si, geçerlilik bitiş tarihi, doğrulama durumu ve UTC doğrulama zaman damgası eklenmiştir.

- unverified: doğrulanmadı; tüm eski demo kayıtların başlangıç durumu.
- review_needed: inceleme gerekli.
- verified: kullanıcı tarafından elle doğrulandı olarak işaretlendi. Kaynak başlığı ve URL zorunludur.
- valid_until: ISO YYYY-MM-DD; boşsa geçerlilik bilinmiyor.
- validity_status: süre geçtiyse expired, bugün veya gelecekteyse current, tarih belirtilmediyse unspecified.

Kaynak URL'si otomatik açılıp içeriği karşılaştırılmaz. Elle doğrulandı ifadesi bağımsız kanıt doğrulaması değil, kullanıcı beyanıdır. Kaynak URL alanına erişilebilmesi doğrulanmaz. Süresi dolmuş cevaplar sohbet ve SSS alanlarında uyarıyla gösterilir; metin otomatik silinmez.

Eski kayıtların içeriği SQLite sütun geçişinde korunur. JSON dışa aktarım, CSV/XLSX içe aktarım ve soru düzenleme formu yeni alanları destekler. Birleştirme geçmişinde kaydın kaynak metadatası da saklanır.

## Sınırlamalar ve kabul

- Model ve büyük Python bağımlılıkları normal Windows BAT dosyasına eklenmedi; isteğe bağlı ikinci BAT dosyasındadır.
- Gerçek model dosyaları GitHub Actions üzerinde indirilmedi. CI, ağsız sahte embedding üreticisiyle API akışını test eder.
- Gerçek modelin CPU performansı ve tarayıcı kullanımı için ayrıca Windows üzerinde kabul testi gerekir.
- Kaynakları elle giren kullanıcılar doğrulama sorumluluğunu taşır.
- SQLite veritabanını yükseltmeden önce faqbot.db yedeği alınmalıdır.
