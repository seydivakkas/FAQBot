# FAQBot — Türkçe E-Ticaret SSS Chatbotu

![Python CI](https://github.com/seydivakkas/FAQBot/actions/workflows/ci.yml/badge.svg)

**FAQBot**, kargo, iade, ödeme ve sipariş konularındaki Türkçe müşteri destek sorularını, örnek mağaza SSS kayıtlarıyla eşleştiren **yerel çalışan, ücretsiz API gerektirmeyen** bir portföy projesidir.

> Bu proje gerçek e-ticaret platformuna bağlı değildir. Ücret, teslimat ve iade koşulları **tamamen kurgusal demo verileridir**.

## Neler yapıyor?

- 4 kategoride toplam 20 örnek soru-cevap ve alternatif ifadeler
- **Arayüzde “20 Soruyu Gör” paneli**: kategori filtreleme, arama, yanıt önizleme ve tek tıkla soru gönderme
- SQLite depolama ve tekrarlanabilir başlangıç veri ekleme
- Türkçe metin normalizasyonu; önce birebir eşleşme
- scikit-learn ile karakter n-gram TF-IDF + cosine similarity
- Düşük benzerlikte **uydurma cevap yerine fallback**
- Mobil uyumlu HTML/CSS/JavaScript sohbet arayüzü
- FastAPI, OpenAPI /docs ve otomatik pytest testleri
- GitHub Actions CI

**Not:** TF-IDF metin benzerliğidir; büyük dil modeli (LLM), semantik garantisi veya gerçek mağaza entegrasyonu değildir.

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

Dosya `%USERPROFILE%\Projects\FAQBot` klasörünü oluşturur veya günceller (`git pull --ff-only`), `.venv` kurar, bağımlılıkları yükler, SQLite'a 20 soruyu aktarır ve **pytest testlerini** çalıştırır. Testler geçerse sunucuyu açar ve `/health` hazır olduğunda tarayıcıda `/app` sayfasını gösterir. Sunucuyu kapatmak için BAT penceresinde **Ctrl+C** kullanabilirsiniz.

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

Veritabanı, sunucu başlangıcında da otomatik hazırlanır. JSON örneklerini değiştirdiğinizde, aynı sorunun güncellenen alanları yeniden başlangıçta SQLite içine aktarılır.

## Adresler

| URL | Açıklama |
| --- | --- |
| http://127.0.0.1:8000/app | Sohbet ekranı; sağ üstte **20 Soruyu Gör** düğmesi |
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

- /app adresini aç; **20 Soruyu Gör** butonuna basıp toplam 20 sorunun (her kategoride 5) listelendiğini doğrula.
- Kategori filtreleri ve arama kutusunu dene, sorunun **Yanıtı önizle** bağlantısını aç, soruya tıklayarak sohbette cevabı gör.
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
  matching.py      normalizasyon, exact ve TF-IDF
data/
  faqs.json        20 kurgu SSS
frontend/
  index.html       sohbet arayüzünün yapısı
  style.css        responsive tasarım
  app.js           POST /chat iletişimi + /faqs paneli
tests/
  conftest.py      izole geçici veritabanı
  test_api.py      HTTP sözleşmesi testleri
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
- Gerçek sipariş sistemi, kullanıcı girişi veya kişisel müşteri verisi kullanılmaz.
- Bu eğitim projesi internet üzerinde üretim dağıtımına hazır bir müşteri destek sistemi değildir.
- LICENSE eklenmemiştir; yeniden kullanım lisansı ayrıca kararlaştırılmalıdır.

## Portföyde kullanım

**Tek cümle:** FastAPI ve SQLite ile geliştirilmiş, Türkçe soru varyasyonlarını TF-IDF ile eşleştiren ve güvenli fallback kullanan e-ticaret SSS web uygulaması.

Ekran görüntüsü eklemek istersen gerçek uygulamadan görsel alıp docs/screenshots/ klasörüne koy; demo görselini çalışmayan bir sahte ekran görüntüsüyle değiştirme.

## Geliştirici

[seydivakkas](https://github.com/seydivakkas)
