# FAQVec-TR — D03 Özgün Türkçe SSS Verisi, Sıfırdan Üretim

**Tarih:** 19 Ekim 2026  
**Kaynak politikası:** [OWNED veya kökeni doğrulanmış CC0](VERI_KAYNAGI_KESIN_POLITIKA.md)  
**Mühendislik kararı:** `ÖZGÜN_TASLAK_HAZIR / ETİKET_İNCELEMESİ_HOLD / TİCARİ_EĞİTİM_HOLD`

## Bu aşamada gerçekten üretilen veri

Bu çalışmada harici soru/cevap veri kümesi, internetten alınmış metin veya başka bir kişinin derlemesi kullanılmadan yeni kurgusal müşteri destek ifadeleri yazıldı.

| Kaynak | Adet | Açıklama |
| --- | ---: | --- |
| Özgün niyet taslağı | 96 | Niyet başına bir kanonik soru ve bir **taslak cevap** |
| Alternatif soru | 192 | Her niyet için 2 anlamca yakın ifade adayı |
| Zor negatif adayı | 48 | Benzer konuda fakat farklı cevap gerektirecek biçimde tasarlanan niyet çifti |
| Yanıtsız kalma adayı | 24 | Temsili SSS bilgi tabanında cevap verilmemesi düşünülen sorgu |
| Konu alanı | 12 | Sipariş, kargo, iade, değişim, ödeme, üyelik, kampanya, ürün, teslimat, destek, fatura ve gizlilik |

**Bu rakamlar etiketlerin doğrulandığı veya modelin başarı kazandığı anlamına gelmez.** Taslakların üretimi proje bağlamında gerçekleşti; tamamen tesadüfi örtüşmeleri dışlayacak evrensel bir telif taraması ya da bağımsız insan değerlendirmesi yapılmadı. Hiçbir müşteri mesajı veya gerçek firma politikası model eğitimine çekilmedi.

### Kaynak dosyaları

- `seed/faqvec_tr_ozgun_taslak_v01.json` — 96 niyet, alternatif ifadeler ve kurgusal süreç cevapları.
- `seed/faqvec_tr_yanitsiz_taslak_v01.json` — insan incelemesi bekleyen 24 yanıtsızlık örneği.
- `scripts/build_faqvec_original.py` — kaynak doğrulama, niyet ailesi bazlı split, SHA-256 ve inceleme paketi.

## Teknik veri sözleşmesi

1. Her niyet bir `intent_id`, `family_id`, `domain`, `question`, `alternatives`, `answer` ve `source_id` taşır.
2. İki benzer fakat farklı cevap gerektiren niyet bir **aile** olarak tutulur. Ailenin tamamı tek bir train/validation/test bölmesine atanır; zor negatiflerin eğitim ve teste bölünmesi önlenir.
3. Niyet kimlikleri ile normalleştirilmiş soru ifadeleri tekrarlanamaz. Başlık ve cevap boş olamaz; e-posta, açık URL veya uzun sayıların soru alanına girmesi reddedilir.
4. Zor negatifler yalnızca `needs_human_review` statüsündedir. **İnsan tarafından onaylanmış zor negatif sayısı sıfırdır.**
5. Yanıtsızlık adaylarının `expected_id=null` olması, bu örneklerin henüz doğru etiketlendiği anlamına gelmez. İlgili veri benchmarka ancak insan değerlendirmesiyle ve ayrı onay kapısıyla girer.
6. Taslak manifestinde `origin_kind=self_authored`, `license_spdx=OWNED` **hedeflenen üretim sınıfını** temsil eder; `rights_review_complete=false` ve `commercial_training_approved=false` olarak korunur. Bu iki alanı kanıtsız değiştirmek yasaktır.
7. Model eğitimi ve ticari dağıtım için gerçek insan kontrolü ile kaynak bütünlüğü, lisans ve bağımsız test kapıları ayrıca gerekir.

## Windows'ta yerel hazırlama

Proje kökündeki sanal ortam kuruluysa:

```powershell
.venv\Scripts\python.exe -m scripts.build_faqvec_original --check-only
.venv\Scripts\python.exe -m scripts.build_faqvec_original --output-dir datasets/faqvec_original_v01
```

İlk komut dış ağ olmadan yalnız katalog doğrular. İkinci komut taslak veri paketini yerel dizinde oluşturur:

- `original_draft.jsonl` — eğitim için **henüz onaysız** niyetler.
- `hard_negative_review.DRAFT.jsonl` — tüm negatif adayları.
- `hard_negatives_train_candidate.DRAFT.jsonl` — yalnız train bölmesine uygun negatif adaylar.
- `no_answer_review.DRAFT.jsonl` — yanıtsızlık adayları.
- `intent_review.DRAFT.jsonl` — 96 niyet için insan değerlendirme şablonu.
- `authorship_evidence.DRAFT.json` — taslağın oluşturulma yöntemi ve katalog SHA-256 kaydı.
- `manifest.DRAFT.json` — haklar ve onay bayrakları `false`.
- `summary.json` — kaynak, bölmeler ve örnek sayımları.

`datasets/` dizini `.gitignore` içindedir; özel inceleme dosyaları kamuya açık GitHub deposuna otomatik eklenmez. Aynı çıktı klasörünün üzerine yazılmaz.

## İnsan inceleme kontrol listesi

Önce 96 kanonik soru/cevap ve 192 alternatif ifadeyi uzman açısından kontrol edin: aynı müşteri ihtiyacı mı, cevap doğru ve bir mağazanın gerçekte sunmadığı bir hizmeti vaat ediyor mu, gerekçesi açık mı? Sonra 48 negatif adayda iki soru gerçekten farklı cevap mı gerektiriyor, başka bir niyetin eşanlamlısı olabilir mi kontrol edin. Son olarak 24 yanıtsızlık adayının bilgi tabanında gerçekten karşılığı olmadığı doğrulanmalı.

**Başarısız, kararsız veya uyuşmayan kayıtlar eğitimden çıkarılmalı.** İnsan incelemecilerinin ayrı kimlikleri, karar tarihleri ve kaynak katalog SHA'sı saklanmalı. Değerlendirme verisi eğitim için kullanılmamalı.

## Model yarışması için açık kapılar

- Kaynak verinin özgünlüğü ve insan etiketleri: **HOLD**
- Nihai kullanım veri kümesinin lisans/kanıt kabulü: **HOLD**
- Bağımsız gerçek müşteri destek testi: **HOLD**
- E5-base / FAQVec-TR / MiniLM / BGE-M3 / TF-IDF karşılaştırması: **HOLD**
- Windows GPU/CPU gecikme, model boyutu, gerçek kullanıcı kabulü: **HOLD**
- Ticari dağıtım: **HOLD**

Önceki 110 demoyla otomatik eğitim ve eski üçüncü taraf D01/D02 indirme/inceleme akışları devre dışıdır. Açık lisanslı model ağırlıkları, eğitim veri kaynaklarından ayrı incelenebilir ancak otomatik indirilmez.

**Sıradaki iş:** D03-02 kapsamında kendi ürettiğimiz veriyi uzman değerlendirmesine alıp açık uyuşmazlıkları çözmek; ardından hakları teyit edilmiş MANIFEST dosyasını kullanıcı onayıyla açmak. Bugün gerçek model ağırlıklarıyla eğitim/benchmark yapılmadı.
