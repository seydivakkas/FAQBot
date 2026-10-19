# FAQVec-TR D05 — Özgün veri kapsamı, yanlış cevap güvenliği ve BGE-M3 yarışı

**Kaynak sözleşmesi:** Yalnız projemiz için sıfırdan yazılan metinler veya hakları doğrulanmış CC0/kamu malı. Bu aşamada hiç dış korpus kullanılmadı. Model ağırlıklarının MIT/Apache-2.0 lisansı, eğitim metinlerinin köken ve yayın haklarından ayrı değerlendirilir.

## 1. D05 ile eklenen veri

Kaynak: `seed/faqvec_d05_ozgun_egitim_ekleri_v01.json`.

- Garanti, teknik servis, kurulum, mağazadan teslim, bildirim ve erişilebilirlik olmak üzere **6 yeni müşteri destek alanı**.
- **24 yeni özgün niyet**, her niyette **1 kanonik soru, 2 alternatif ifade ve 1 kurgusal cevap**; toplam **48 yeni alternatif**.
- D03'ün 74 özgün eğitim niyetindeki iki alternatifin tamamı kullanılarak **148 çift** ve D05'in 24×2=**48** yeni çifti: **196 eğitim çifti**.
- Yeni 24 niyetin tamamı `split=train`, `train_only_auxiliary=true`; mevcut 96 soruluk D04 galerisine, doğrulama ve teste **EKLENMEZ**.
- D03-02'deki yalnız eğitim ailesine ait 28 olası AI zor negatif arasından train'e düşenler isteğe bağlı ikinci aşamada kullanılır; sıfır insan/bağımsız etiket uydurulmaz.
- Dosya kökeni Git blob SHA `b5fbf9135fd286852c4f441fa8e28833ff008d60` ile sabittir. Değişen taslak sessizce eğitim onayı alamaz.
- `commercial_training_approved=false`, `rights_review_complete=false`, `human_review=not_performed` açıkça korunur.

## 2. Güvenlik politikası

Uygulama: `app/faqvec_d05_policy.py`. İki hata türü ayırt edilir:

1. Yanlış SSS niyetini doğruymuş gibi yanıtlamak (**pozitif yanlış eşleşme**).
2. SSS kapsamı dışında veya özel veri talebinde bulunan soruyu bilgi varmış gibi yanıtlamak (**false answer / OOS**).

201 sabit eşik (0,000–1,000, 0,005 adım) üzerinde yalnız doğrulama skorlarına bakılır. Seçim için her iki yanlış cevap oranının da validation üzerinde **en fazla %10** olması şarttır. Uygun eşikler içinde doğru cevaplanabilen pozitif soru sayısı en yüksek olan tercih edilir. Tam eşitlikte daha yüksek eşik seçilir. Eşik seçimi sırasında test etiketleri ve skorları kullanılmaz.

Bu kısıtlar **validation'a aittir**; sonuçlar testte de %10 garantisi oluşturmaz. Yeni test sonucunun aynı güvenlik sınırlarını aşıp aşmadığı ayrı gösterilir. Eşik çok yüksek olduğu için hiçbir soruya cevap verilemiyorsa `usable_on_validation=false` kaydı bırakılır; sıfır yanlış cevap başarı sayılmaz.

Karşılaştırma raporu hem D04'ün ceza-maliyet eşiğini hem D05 güvenlik kısıtlı eşiğini, her ikisinin **aynı test veri kümesindeki** toplam doğruluğunu, pozitif abstention değerini, false-answer ve yanlış eşleşme sayısını yayımlar. Çizim için 41 noktalı validation coverage-risk eğrisi ve ayrı test göstergeleri bulunur.

## 3. Yanıtsızlık güvenlik dilimleri

`scripts/faqvec_d05_safety_slices.py` mevcut ve yalnız AI etiketli 22 OOS sorusunu dört sınıfa ayırır: **kişisel/hesap güvenliği (10)**, **gizli kurum içi bilgi (5)**, **doğrulanamayan anlık/gelecek bilgi (5)**, **hukukî/tıbbî uzman kararı (2)**. Mevcut 11 validation / 11 test OOS örneği yerinde kalır; bu sınıflandırma gerçek kullanımda kişisel veri açıklama yetkisi vermez.

Bu 22 sorunun tamamı kurgusaldır. Bunların önemli bölümü bariz yasak/özel bilgi isteği olduğundan, genel müşteri desteğindeki bilinmeyen fakat zararsız soruları temsil ettiği varsayılamaz. Ayrı bağımsız OOS kümesi ticari kabul için gerekir.

## 4. Kontrollü gerçek model ablation deneyi

**Kanıt iş akışı:** [FAQVec D05 gerçek E5 eğitim ve model yarışı](https://github.com/seydivakkas/FAQBot/actions/workflows/faqvec-d05-real-models.yml).

| Deney | Başlangıç ağırlıkları | Kullanılan veri | Holdout |
|---|---|---|---|
| TF-IDF | Model ağırlığı yok | Mevcut 96 kanonik galeri | D04 sabit |
| E5-base | MIT E5-base | Fine-tune yapılmamış | D04 sabit |
| FAQVec-D04 kontrol | Aynı MIT E5-base | 74 tek alternatif çifti; 1 epoch | D04 sabit |
| FAQVec-D05 aday | Aynı MIT E5-base | 196 pozitif çift + train-only AI negatifler; 1 epoch + 1 negatif aşaması | D04 sabit |
| MiniLM | Apache-2.0 | Fine-tune yapılmamış | D04 sabit |
| BGE-M3 | MIT, sabit güvenli safetensors revizyonu | Fine-tune yapılmamış | D04 sabit |

Deney CPU GitHub Actions üzerinde gerçek ağırlıklarla koşturulacaktır. Kod, GPU olmaması veya bir modelin yüklenememesi halinde **uydurma Recall/hız sonucu üretmez**. Her koşu ağırlık SHA, kaynak revizyonu, eğitim manifesti, yalnız validation eşiği ve gerçek test raporunu ayrı tutar. Ağırlıklar GitHub artifact'ına yüklenmez.

Önemli yöntem sınırlaması: D05 değişikliği, hem **ikinci alternatiflerin** hem **yeni 24 eğitim niyetinin** hem de **AI-negatif ikinci aşamasının** birleşik etkisini ölçer. Tek tek her bileşenin nedensel etkisini anlamak için ayrıca ablasyon koşuları gerekir. Mevcut sabit test çok küçük (12 niyet / 24 pozitif + 11 OOS), AI etiketli ve aynı üretim yöntemine aittir.

## 5. Windows 11 / RTX 4070 yerel komutları

Proje kökünde mevcut sanal ortamla ilk hazırlık + açık model indirme + yeni aday eğitimi + karşılaştırma:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_faqvec_d05_windows.ps1 -InstallDependencies -DownloadModels -Train -Compare
```

Önceden indirilmiş modeller ve iki yerel eğitim ağırlığı hazırsa internet olmadan yalnız karşılaştırma:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_faqvec_d05_windows.ps1 -Compare
```

`-Compare` için eski D04 modelinin `models\faqvec-tr-ai-research\model` içinde bulunması gerekir. Eski modeli değiştirmemek esastır; `-D04Model` ile başka mevcut yerel yol seçilebilir. D05 çıktısı zaten varsa üzerine yazılmaz. RTX sürücüsü ile PyTorch CUDA uyumu fiziksel bilgisayarda ayrıca doğrulanmalıdır. Gerçek Windows/Edge/offline paket kabulü bu aşamada yapılmış sayılmaz.

## 6. Kabul etiketleri

**Yazılım/veri altyapısı:** Kaynak hash, sızıntı ve 201 eşik testleri CI'da doğrulandığında PASS. **Model performansı:** yalnız gerçek tamamlanmış altılı yarış ve test güvenlik kontrolleriyle ayrı değerlendirilir; başarı garanti edilmez. **Ticari yayın:** kaynak veri hakları, bağımsız gerçek müşteri testleri, lisans NOTICE/SBOM ve Windows fiziksel kabul sağlanana kadar HOLD.

**Mühendislik kararı:** `D05_ÖZGÜN_TRAIN_VERİSİ_ADAY_PASS / VAL_ONLY_KALİBRASYON_ADAY_PASS / GERÇEK_MODEL_KARŞILAŞTIRMA_KANIT_BEKLİYOR / BAĞIMSIZ_SAHA_HOLD / TİCARİ_YAYIN_HOLD`.
