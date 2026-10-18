# v1.6 — Çöp Kutusu ve Geri Alınabilir SSS Silme

## Amaç ve veri modeli

- `faqs.deleted_at` alanı eski veritabanlarına `ALTER TABLE` ile eklenir. `NULL` **aktif**, UTC zaman damgası **silinmiş** kayıt demektir.
- Silme işlemi artık `UPDATE faqs SET deleted_at = ...` kullanır; ID, soru, cevap, kategori, alternatif sorular, kaynak URL/başlığı, geçerlilik tarihi ve doğrulama bilgileri aynı SQLite satırında korunur.
- `GET /faqs`, `POST /chat`, JSON dışa aktarma ve benzer soru taraması sadece aktif kayıtları kullanır. Silinmiş soru chatbot tarafından doğrudan sunulmaz.
- Silinme anı `deleted_at` UTC zaman damgasıyla izlenir ve **Ayarlar → Çöp Kutusu** bölümünde listelenir.
- `GET /faqs/trash` ve `POST /faqs/trash/{id}/restore` yönetim uç noktaları sadece localhost erişimine açıktır. Geri yükleme `{"confirm": true}` gerektirir.

## Geri yükleme güvenliği

- İşlem SQLite `BEGIN IMMEDIATE` transaction'ında yapılır; sistem silinen soruyu ve tüm alternatif ifadeleri **aktif** soru/alternatiflerle Türkçe normalizasyon sonrası karşılaştırır.
- Herhangi bir ifade çakışırsa HTTP 409 döner ve **hiçbir alan değiştirilmez**. Sorun çözüldükten sonra yeniden denenebilir.
- Çöp kutusunda olmayan ID geri yüklenemez (HTTP 404). Aynı silme isteği ikinci kez 404 verir.
- Birleştirme sonucu arşivlenen SSS'ler de silinmiş olarak saklanır; birleşen ifadeler korunan soruya taşındığı için bu kaydı doğrudan geri yükleme sırasında çakışma oluşabilir. Önce aktif kayıttaki alternatif ifadeleri incelemek gerekir.
- Mevcut `question UNIQUE` kısıtlaması korunmuştur. Silinen kaydın *aynı ana soruyla* tekrar oluşturulması engellenir; kaydın **Çöp Kutusu’ndan geri yüklenmesi** gerekir. Bu, veri taşıma sırasında SQLite tablosunun yıkıcı biçimde yeniden kurulmasını önler.
- **Kalıcı silme API'si bulunmaz**. Çöp Kutusu kayıtları kendiliğinden temizlenmez; kullanıcı veri dosyasını bilerek silmedikçe korunur.

## Kullanım

1. FAQBot'ta Ayarlar'ı açın.
2. Mevcut sorular listesinden **Sil** düğmesine basın ve Çöp Kutusu'na taşıma işlemini onaylayın.
3. **Çöp Kutusu — Silinen Soru ve Cevaplar** bölümünde soru/cevap metniyle arama yapın.
4. İlgili satırda **Geri yükle** düğmesini seçip onaylayın.
5. Kayıt aynı ID ile etkinleşir; sohbet ve SSS listesi güncellenir.

## Veritabanı geçişi ve sınırlamalar

Mevcut SQLite ve ilk 110 örnek kayıt silinmez. Sürüm yükseltme `deleted_at` sütununu ekler; önceki 1.5 veya daha eski sürümde **kalıcı olarak silinmiş** kayıtlar sonradan geri üretilemez. Geri yükleme yalnızca v1.6 sonrasında Çöp Kutusu'na taşınan kayıtlar içindir.

Yükseltmeden önce `faqbot.db` dosyasının yedeği alınmalıdır. Bu özellik JSON dosyasından içe aktarmanın yerini tutmaz; JSON geri alma sonraki geliştirme paketidir.

Gerçek Windows tarayıcı kabulü otomatik Linux/Windows CI testlerinin yerine geçmez; UI açılarak son kullanıcı kabulü ayrıca yapılmalıdır.
