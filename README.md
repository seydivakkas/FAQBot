# FAQBot — Türkçe E-Ticaret SSS Chatbotu

![Python CI](https://github.com/seydivakkas/FAQBot/actions/workflows/ci.yml/badge.svg)

**FAQBot**, kargo, iade, ödeme ve sipariş konularındaki Türkçe müşteri destek sorularını, örnek mağaza SSS kayıtlarıyla eşleştiren **yerel çalışan, ücretsiz API gerektirmeyen** bir portföy projesidir.

> Bu proje gerçek e-ticaret platformuna bağlı değildir. Ücret, teslimat ve iade koşulları **tamamen kurgusal demo verileridir**.

## Neler yapıyor?

- 8 kategoride toplam **110 farklı demo müşteri ihtiyacı**, 2 veya daha fazla alternatif soru ifadesi
- **Arayüzde “Soruyu Gör” paneli**: kategori filtreleme, arama, yanıt önizleme ve tek tıkla soru gönderme
- **Ayarlar / SSS Yönetimi**: soru-cevap CRUD, yedek alma, CSV/XLSX toplu aktarım, benzer soru önerileri, kayıt birleştirme insan etiketli hatalı eşleşme incelemesi ve geri alınabilir silme
- SQLite depolama: ilk 20 kayıt korunur, v1.3 için 90 yeni aday kayıt bir kerelik eklenir; kullanıcı düzenlemeleri yeniden başlatmada korunur
- Türkçe metin normalizasyonu; önce birebir eşleşme
- scikit-learn ile karakter n-gram TF-IDF + cosine similarity
- Düşük benzerlikte **uydurma cevap yerine fallback**
- Mobil uyumlu HTML/CSS/JavaScript sohbet arayüzü
- FastAPI, OpenAPI /docs ve otomatik pytest testleri
- GitHub Actions CI

**Not:** Sohbet hâlâ TF-IDF kullanır; embedding yöntemi isteğe bağlı yalnızca tekrar soru taramasına uygulanır. Hiçbir yöntem aynı anlamı kesin kanıtlamaz.

## FAQVec-TR v0.2 — MIT E5 tabanlı ticari odaklı araştırma sürümü

- **Temel model:** [intfloat/multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) (MIT, 768 boyut). Üründe bu türevin kökeni ve MIT bildirimleri korunacak. Daha güçlü karşılaştırma modeli: [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) (MIT).
- **Yalnızca açık kullanıcı komutuyla kurulum:** [setup_faqvec_v2_windows.bat](setup_faqvec_v2_windows.bat). Normal FAQBot kurulumu ücretli API veya model indirmesi gerektirmez.
- **Eğitim:** `scripts/train_faqvec_v2.py` ile yerel E5 üzerinde MultipleNegativesRankingLoss; yanlış negatifleri azaltan NO_DUPLICATES; insan onaylı zor negatiflerle ayrı ince ayar.
- **Veri sözleşmesi:** `app/faqvec_v2_data.py` lisans/kaynak incelemesi, SHA-256, niyet düzeyinde train-validation-test ayrımı. 110 demo SSS yalnızca deney; ticari veri izni otomatik verilmez.
- **Yarışma altyapısı:** `scripts/benchmark_faqvec_v2.py`, aynı test galerisiyle TF-IDF, E5-base, FAQVec-TR v0.2, MiniLM ve BGE-M3 modellerini Recall@1/5, yanlış cevap, yanıtsız bırakma ve yanlış cevap verme oranlarında karşılaştırır.
- **Önemli:** Kod ve otomatik testler hazır. E5'in yaklaşık 1 GB'lık ağırlıkları henüz bu depoya indirilmedi; tam ince ayar ve bağımsız gerçek veri yarışması tamamlanmadı. Ticari ürün kabulü `HOLD`.

[Ayrıntılı v0.2 eğitim ve ticari kabul sözleşmesi](docs/faqvec_tr_v2_arastirma.md)

## FAQVec-TR v0.1 — Kendi sıfırdan eğitilen embedding modelimiz

- FAQVec-TR, 48 boyutlu Türkçe n-gram tabanlı öğrenilebilir encoder'ımızdır; dışarıdan hazır model ağırlığı indirmez.
- Eğitim: scripts/train_faqvec_tr.py, Windows: setup_faqvec_windows.bat.
- Eğitim verisi: ilk 110 demo SSS ve alternatifleri. Eğitim ve çıkarım offline çalışır.
- Her modelin weights.npz ve manifest.json dosyası sürüm, checksum ve veri kökeni taşır. models/ Git'e eklenmez.
- Ayarlar > Benzer Sorular alanında FAQVec-TR seçilebilir. Mevcut TF-IDF / MiniLM seçeneği korunur.
- **Ticari kabul HOLD:** model performansı ve veri kullanım hakları bağımsız doğrulanmalı.

[FAQVec-TR teknik sözleşmesi ve ticari kabul koşulları](docs/faqvec_tr_ticari_model.md)
## v1.6 — SSS Çöp Kutusu ve Geri Yükleme

- Ayarlar'da **Çöp Kutusu — Silinen Soru ve Cevaplar** ekranı; silinmiş soruların cevapları, kategori bilgileri ve UTC silinme zamanları görünür.
- **Sil** artık kalıcı silme değil, `deleted_at` zaman damgası ekleyen *soft delete* işlemidir.
- **Geri yükle** ile kayıt orijinal ID ve tüm alanlarıyla geri alınır; diğer aktif kayıtlardaki aynı ana/alternatif sorularla çakışmada HTTP 409 verilir.
- Sohbet, arama, JSON yedeği ve benzer soru tespiti yalnızca etkin SSS'leri içerir.
- Çöp Kutusu'ndaki ana sorular aynı metinle yeniden oluşturulamaz; önce çöp kutusundan geri yükleme yapılmalıdır. Kalıcı silme bu sürümde yoktur.
- **Kılavuz:** [Çöp Kutusu ve güvenli geri yükleme](docs/cop_kutusu_ve_geri_yukleme.md).

## v1.5 — Hatalı Eşleşme İnceleme Paneli

**Ayarlar → Hatalı Eşleşme İncelemesi** bölümünde sohbet eşleşmelerini yönetici kontrolünde inceleyebilirsiniz.

- Günlük toplama **varsayılan olarak kapalıdır**. Ayarlardan etkinleştirildiğinde yalnızca bu bilgisayardan gönderilen yeni sohbetlerin sorusu, eşleşen SSS kimliği, tarih, verilen cevap, eşleştirme türü (`exact`, `tfidf`, `none`) ve skor kaydedilir.
- Veriler **yalnızca SQLite** içindedir; IP, cihaz/oturum bilgisi veya çerez alanı saklanmaz. Açıkça görünen e-posta, URL veya uzun numara içeren bazı mesajlar kayıt dışı bırakılır; **kişisel veri temizleme garantisi yoktur**. Gerçek kişilerle testte açık bilgilendirme ve izin gereklidir.
- En son **1.000 sohbet kaydı** tutulur; limit aşılırsa en eski kayıtlar silinir. Günlük kapatılınca eski kayıtlar korunur, yeni kayıt eklenmez.
- Her kayda `Bekleyen`, `Doğru`, `Yanlış` veya `Kararsız` etiketi verilebilir. Yanlış işaretlenen kayıtta beklenen doğru SSS veya **cevap verilmemeliydi** seçilir. Etiketsiz ve kararsız sorular başarı metriğine katılmaz.
- **TF-IDF / embedding performansını hesapla**: aynı insan etiketli sorular GÜNCEL bilgi tabanında yeniden değerlendirilir. Sohbet TF-IDF eşiği **0.40**, karşılaştırma embedding eşiği **0.70** olarak gösterilir. Bu farklı eşikler kalibre edilmiş olasılıklar değildir.
- Yerel embedding kurulmamışsa karşılaştırma arayüzü bunu belirtir; yalnızca TF-IDF sonucu hesaplanabilir. Model hiçbir zaman otomatik indirilmez.
- İnsan etiketine göre güncel SSS kimliği silinmiş kayıtlar kapsam dışı bırakılır. Yanıtlar eğitim kümesinden seçilmiş veya az sayıda ise başarı oranı **genelleştirilemez**.
- **Günlüğü temizle** seçeneği ikinci kez onay alarak bütün yerel inceleme etiketlerini ve kayıtlarını siler. Otomatik silme geri alma bu aşamada yoktur.
- Yalnızca localhost yönetim API uç noktaları: `GET/PUT /reviews/settings`, `GET /reviews`, `PATCH /reviews/{id}`, `POST /reviews/evaluate`, `DELETE /reviews` (onaylı).

**Not:** Günlükler sadece yönetici tarafından açıldıktan sonra oluşur. Kullanıcı sorularını kayıt altında tutmadan önce gerçek kullanım bağlamında kişisel veri ve izin gerekliliklerini değerlendirin. Gerçek model performansı henüz bağımsız gerçek veriyle doğrulanmadı.

## v1.4 — Yerel embedding ve kaynak bilgileri

- Her SSS kaydında kaynak başlığı, URL, geçerlilik tarihi, elle doğrulama durumu ve geçerlilik uyarısı.
- Ayarlar'da **TF-IDF** veya yalnızca yerel klasörden yüklenen **çok dilli embedding** yöntemi.
- İsteğe bağlı model kurulumu: [setup_embedding_windows.bat](setup_embedding_windows.bat). Temel kurulum model indirmez.
- JSON dışa aktarma ve Excel/CSV aktarımında kaynak alanları korunur.
- Ayrıntılı sözleşme ve sınırlamalar: [Yerel model ve kaynak yönetimi](docs/yerel_embedding_ve_kaynak.md).

## Mimari

~~~text
Tarayıcı: /app (HTML + CSS + JS)
          |
          v
POST /chat (FastAPI)
          |
          v
normalize -> exact match -> TF-IDF (char_wb 2–5) -> eşik 0.40
          |                                      |
          v                                      v
SQLite / JSON örnekleri                    düşük skor -> fallback
~~~

Backend ve statik arayüz aynı origin üzerinden sunulur; ücretli API anahtarı kullanılmaz.

## Gereksinimler

- Python 3.11 veya üstü (Python 3.12 önerilir)
- Git (klonlamak için)

## Windows tek tıkla otomatik kurulum (.bat)

Windows 10/11 bilgisayarınızda **Git for Windows** ve **Python 3.12 (py launcher dahil)** yüklüyse şu dosyayı çalıştırın:

[`setup_windows.bat`](setup_windows.bat)

Dosya `%USERPROFILE%\Projects\FAQBot` klasörünü oluşturur veya günceller (`git pull --ff-only`), `.venv` kurar, bağımlılıkları yükler, SQLite'a başlangıçta 110 demo soruyu aktarır ve **pytest testlerini** çalıştırır. Testler geçerse sunucuyu açar ve `/health` hazır olduğunda tarayıcıda `/app` sayfasını gösterir. Sunucuyu kapatmak için BAT penceresinde **Ctrl+C** kullanabilirsiniz.

**Önemli:** Yerel Git değişiklikleriniz otomatik silinmez; `git pull --ff-only` güncellemeyi reddederse değişiklikleri kendiniz değerlendirin. İnternete ilk kurulumda Git klonlamak ve Python paketlerini yüklemek için ihtiyaç vardır; sohbet işlevleri yerel çalışır.

Sadece kurulum ve testleri yapmak (sunucu/tarayıcı açmadan):

~~~bat
setup_windows.bat --check-only
~~~

## Windows kurulumu (PowerShell)

~~~powershell
git clone https://github.com/seydivakkas/FAQBot.git
cd FAQBot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.database
python -m uvicorn app.main:app --reload
~~~

Python 3.12 yüklü değilse sanal ortam oluşturma komutunda sisteminizdeki uygun Python sürümünü kullanın (ör. py -m venv .venv).

## Linux / macOS

~~~bash
git clone https://github.com/seydivakkas/FAQBot.git
cd FAQBot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.database
python -m uvicorn app.main:app --reload
~~~

Veritabanı sunucu açılırken hazırlanır. `data/faqs.json` içindeki ilk 20 örnek yalnızca ilk kurulumda eklenir. **v1.3 yükseltmesinde `data/faqs_v13_additions.json` dosyasındaki 90 yeni soru mevcut veritabanına bir kez eklenir.** Bu ekleme, mevcut kayıtların soru veya cevaplarını değiştirmez; aynı ana soruya sahip kayıtlar atlanır. Bir kez eklenip sonradan silinen sorular tekrar oluşmaz. İçe aktarma yapılmadan önce `faqbot.db` dosyanızın yedeğini alın.

110 sayısı temiz ilk kurulum için geçerlidir. Mevcut veritabanında silinen/düzenlenen kayıtlar veya aynı soru başlığı bulunuyorsa sayı farklı olabilir. Güncellemeler eski kayıtların silinmesini veya zorla yeniden yazılmasını amaçlamaz. **Yeni 90 cevaplar gerçek mağaza politikası değil, kurgu demo senaryolarıdır**; canlı kullanıcıya yönelik doğrulanmış kaynak olarak sunulamaz.

### Benzer soru tespiti ve ayarlanabilir eşik (v1.3.2)

**Ayarlar → Benzer Soruları İncele** alanında eşik değeri hem **kaydırıcı** hem **sayısal yüzde alanı** ile %40–95 arasında, %1 adımlarla seçilebilir. **Başlangıç eşiği %70'tir.** Önce **Eşiği kaydet**, ardından **Benzerleri tara** düğmesine basın. Seçim SQLite'ın `app_metadata` tablosunda saklandığından uygulama yeniden açıldığında korunur.

Önemli sınırlar:

- Ayarladığınız oran yalnızca **yönetim ekranındaki tekrar adaylarını** etkiler. Sohbet motorunun `app/matching.py` dosyasındaki **0.40 cevap eşleştirme eşiği değişmez**.
- Yöntem, Türkçe normalize edilmiş ana ve alternatif sorular arasında **karakter TF-IDF (%70 ağırlık) + kelime TF-IDF (%30 ağırlık)** kosinüs benzerliğidir. Skor, aynı anlama gelme olasılığı veya doğrulanmış semantik eşdeğerlik değildir.
- Her adayda **sorular, cevaplar, kategoriler ve eşleşen ifadeler** karşılaştırılır. Farklı kategorilerdeki çiftler gösterilebilir fakat birleştirilemez.
- **Birleştirme kendiliğinden yapılmaz.** Yönetici hangi kaydın korunacağını seçip ayrı onay verir. Korunan cevabın üzerine yazılmaz; kaldırılan kaydın sorusu/alternatifleri korunan kayda eklenir.
- Cevaplar farklıysa arayüz uyarı verir. Birleştirilen her çiftin öncesi/sonrası `faq_merge_history` tablosunda saklanır; fakat geçmişten otomatik **geri yükleme arayüzü henüz yoktur**.
- Başka kayıtla ifade çakışması, %70 gibi kaydedilmiş eşiğin altında kalma, 15 alternatif ifade sınırının aşılması veya işlem sırasında kayıt değişikliği varsa birleştirme yapılmaz.
- API: `GET /settings/duplicates`, `PUT /settings/duplicates`, `GET /faqs/duplicates`, `POST /faqs/duplicates/merge`. Tamamı yerel erişim kontrolüne tabidir.

**Uyarı:** Benzerlik sonuçlarını insan incelemesi olmadan kesin tekrar saymayın; şu an yerel embedding/LLM tabanlı semantik arama bulunmuyor. Kalibrasyon için gerçek sorulardan ayrı değerlendirme kümesi oluşturulmalıdır.

### Excel / CSV toplu aktarımı (v1.3.1)

**Ayarlar → Excel / CSV toplu aktarım** bölümünde dosya seç, **Dosyayı önizle** düğmesine bas, uygun/çakışan/hatalı satırları incele. Sadece **Eklenebilir** satırları onaylamak için **Uygun satırları aktar** seçeneğini kullan.

- [Örnek CSV şablonu](frontend/faq_import_template.csv).
- Sütunlar: `question`, `answer`, `category`, isteğe bağlı `alternative_questions`. Türkçe başlıklar (`soru`, `cevap`, `kategori`, `alternatif_sorular`) da desteklenir.
- CSV **UTF-8** olmalı. Alternatif sorular aynı hücrede `|` ile ayrılır. Excel için `.xlsx` ilk çalışma sayfası okunur; eski `.xls` desteklenmez.
- Sınırlar: dosya **2 MB**, en fazla **500** veri satırı. Kategoriler: `kargo`, `iade`, `odeme`, `hesap`, `siparis`, `urun`, `kampanya`, `destek`.
- Önizleme yalnızca normalize edilmiş aynı soru ve alternatif ifade çakışmalarını saptar; anlamsal olarak benzer farklı ifadeleri belirleme sonraki geliştirmedir.
- Kaydetme anında SQLite üzerinde tekrar denetlenir. Arada kayıt değiştiyse 409 ile **bütün aktarım iptal edilir**, kısmi ekleme veya mevcut cevabın üzerine yazma olmaz.
- Yerel API: `POST /faqs/import/preview` (multipart `file`) ve `POST /faqs/import/commit` (JSON `{"records": [...]}`).
- **Mevcut sorular** listesindeki her satırda **Düzenle** ve **Sil** butonları bulunur; silme onay ister. Geri alma/geri yükleme bu sürümde henüz yoktur.

Öncesinde güncel `faqbot.db` dosyasını veya Ayarlar'daki JSON yedeğini saklayın.

### SSS kayıtlarını yönetme

`http://127.0.0.1:8000/app` adresinde üstteki **⚙ Ayarlar** düğmesine tıklayın:

1. **+ Yeni soru** ile ana soru, cevap, kategori ve her satıra bir alternatif soru girip **Kaydet**'e basın.
2. **Mevcut sorular** alanında arama yapın; **Düzenle** butonuyla alanları değiştirebilirsiniz.
3. Her kayıt satırında **Düzenle** ve **Sil** bulunur. Düzenlenen kaydın formunda da **Kaydı sil** vardır.
4. **JSON yedeği indir** ile kayıtların anlık dışa aktarımını kaydedin.
5. **Soruyu Gör** paneli ve `POST /chat` yeni kayıtları hemen kullanır; sunucuyu yeniden başlatmak gerekmez.

Yönetim uç noktaları: `POST /faqs`, `PUT /faqs/{id}`, `DELETE /faqs/{id}`, `GET /faqs/export`. Düzenleme işlemleri **yalnızca loopback / localhost bağlantılarına** ve aynı-origin tarayıcı isteklerine açıktır. **Bu bir giriş/şifre sistemi değildir:** bilgisayarın yerel oturumunu kullanan herkes kayıtları düzenleyebilir. Uygulamayı internete veya yerel ağa açmayın; çok kullanıcılı kullanım için kimlik doğrulama ve yetkilendirme gerekir.

**Yedekleme:** Yerel kayıtlar `faqbot.db` içinde tutulur. .gitignore nedeniyle GitHub'a yüklenmez. Yeniden kurulum veya bilgisayar değişikliğinden önce Ayarlar'dan JSON yedeğini indirin veya sunucu kapalıyken `faqbot.db` dosyasını ayrıca yedekleyin. JSON yedeğini uygulamaya geri yükleme özelliği bu sürümde bulunmamaktadır.

## Adresler

| URL | Açıklama |
| --- | --- |
| http://127.0.0.1:8000/app | Sohbet ekranı, **Soruyu Gör** ve **⚙ Ayarlar** düğmeleri |
| http://127.0.0.1:8000/docs | Etkileşimli API belgeleri |
| http://127.0.0.1:8000/health | Servis sağlık kontrolü |
| http://127.0.0.1:8000/faqs | JSON soru listesi |

### Örnek API isteği

~~~http
POST /chat
Content-Type: application/json

{"message": "Kargom ne zaman gelir?"}
~~~

Örnek yanıt:

~~~json
{
  "answer": "Örnek mağazamızda siparişler genellikle 1-3 iş günü içinde teslim edilir.",
  "matched_question": "Kargom ne zaman gelir?",
  "category": "kargo",
  "match_type": "exact",
  "match_score": 1.0
}
~~~

Bilinmeyen sorularda match_type alanı none ve category alanı null döner. Boş/yalnızca boşluk içeren veya 500 karakterden uzun mesajlar 422 ile reddedilir.

## Testler

~~~bash
python -m pytest -v
python -m scripts.compare
~~~

Pytest, her API testinde geçici SQLite kullanır ve gerçek faqbot.db dosyasına dokunmaz.

### Manuel arayüz kabulü

- /app adresini aç; **Soruyu Gör** butonuna basıp temiz kurulumda 8 kategoride toplam 110 sorunun listelendiğini doğrula.
- Kategori filtreleri ve arama kutusunu dene, sorunun **Yanıtı önizle** bağlantısını aç, soruya tıklayarak sohbette cevabı gör.
- **Ayarlar** bölümünden yeni soru ekle, yanıtı değiştir, alternatif soru ekle ve sil. Uygulamayı yeniden açıp kalıcılığı kontrol et.
- Örnek Kargo butonuna bas.
- Alternatif bir iade sorusu yaz; kayıtlı cevapla eşleşmeyi incele.
- Alakasız bir soru gönder; fallback çıktısını kontrol et.
- Enter ve Gönder butonlarının çalıştığını doğrula.
- F12 ile dar mobil ekranda taşma olup olmadığını kontrol et.
- F12 Network'te POST /chat isteğini ve 200 durumunu gözlemle.
- Sunucuyu durdurduğunda yeni isteğin başarısız olması beklenir; bağlantı hatası için sunucu çalışırken DevTools Network Offline modunu da kullanabilirsin.

## Proje dosyaları

~~~text
app/
  main.py          FastAPI endpoint'leri ve sayfa sunumu
  database.py      SQLite + JSON veri kaynağı
  importer.py      CSV/XLSX önizleme ve atomik içe aktarma
  matching.py      normalizasyon, exact ve TF-IDF
data/
  faqs.json                  İlk 20 kurgu SSS
  faqs_v13_additions.json    90 yeni kurgu SSS, her biri 2 alternatif ifadeli
frontend/
  index.html       sohbet arayüzünün yapısı
  style.css        responsive tasarım
  app.js           POST /chat iletişimi + /faqs paneli + SSS yönetimi
  faq_import_template.csv   Örnek CSV aktarım şablonu
tests/
  conftest.py      izole geçici veritabanı
  test_api.py      HTTP sözleşmesi testleri
  test_settings.py SSS CRUD / kalıcılık / erişim testleri
  test_import.py   Toplu aktarım, güvenlik ve atomiklik testleri
  test_v13_seed.py  110 örnek / sürümlü veri geçişi
  test_matching.py benzerlik motoru testleri
scripts/
  compare.py       eski yöntem / TF-IDF karşılaştırması
.github/workflows/
  ci.yml           Linux pytest + Windows BAT smoke
setup_windows.bat  Windows tek tıkla kurulum
~~~

## Tasarım kararları ve sınırlamalar

- Küçük veri seti için her /chat isteğinde TF-IDF yeniden oluşturulur; daha büyük veri setinde indeksleme ve cache gerekir.
- SQLite kullanımı demo için yeterlidir; yoğun eşzamanlı prod ortamı hedeflenmemiştir.
- Eşik (0.40) örnek amaçlıdır; bağımsız Türkçe değerlendirme seti üzerinde kalibre edilmelidir.
- Gerçek sipariş sistemi, kullanıcı girişi veya canlı müşteri sistemi kullanılmaz. İnceleme günlüğü açıkken sohbet metinleri kişisel veri içerebileceğinden kullanım öncesi izin ve gizlilik değerlendirmesi gerekir.
- Bu eğitim projesi internet üzerinde üretim dağıtımına hazır bir müşteri destek sistemi değildir.
- LICENSE eklenmemiştir; yeniden kullanım lisansı ayrıca kararlaştırılmalıdır.

## Portföyde kullanım

**Tek cümle:** FastAPI ve SQLite ile geliştirilmiş, Türkçe soru varyasyonlarını TF-IDF ile eşleştiren ve güvenli fallback kullanan e-ticaret SSS web uygulaması.

Ekran görüntüsü eklemek istersen gerçek uygulamadan görsel alıp docs/screenshots/ klasörüne koy; demo görselini çalışmayan bir sahte ekran görüntüsüyle değiştirme.

## Geliştirici

[seydivakkas](https://github.com/seydivakkas)
