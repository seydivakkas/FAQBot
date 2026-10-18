# FAQVec-TR-V2-D02 — Veri Hakları ve İki Bağımsız İncelemeci

## Kesin kaynak kaydı

Veri kaynağı: https://huggingface.co/datasets/dogukanvzr/ml-paraphrase-tr
Sabit kaynak revizyonu: b9d5707470340db13d788a338e7f7897c5e29932
Özgün dosyanın SHA-256 değeri: 2c5bace5f34bbc9bc79084ddf57bc5a298310eaa2614beb9f7862a16b674e39d
Kaynak kartındaki lisans: Apache-2.0 beyanı. Özgün Türkçe cümlelerin üçüncü taraf telif hakkı zinciri henüz bağımsız kanıtlanmadı.

## 1. Kaynak sahibinden alınması gereken açıklamalar

Veri kümesi yayıncısına Hugging Face Community üzerinden aşağıdaki sorular iletilebilir. Bu iletişim HENÜZ GÖNDERİLMEDİ; yayıncıdan bir yanıt alındığı iddia edilmez.

1. 60.000 cümlenin özgün kaynakları nelerdir? Metinler özgün yazım, izinli korpus, otomatik üretim veya üçüncü taraf siteden alıntı mı?
2. Apache-2.0 lisansını bütün cümle çiftlerine uygulama yetkinizi doğrulayacak kayıt veya hak sahibi izni var mı?
3. Veriyi ücretli Türkçe embedding ürününün eğitimi ve ince ayarı için kullanmamız açıkça serbest mi?
4. İnce ayarlanmış model ağırlıklarını ticari müşterilere offline uygulamayla dağıtmak için özel şart veya ek izin gerekiyor mu?
5. Kaynak metinler kişisel veri, haber/eser alıntısı, lisans kısıtlı kaynak veya diğer üçüncü taraf hakları içeriyor mu?
6. Zorunlu atıf/NOTICE, yeniden dağıtım ve saklama koşulları nelerdir?
7. Pozitif/negatif etiketler nasıl oluşturuldu? D01 denetiminde gözlenen 44.995/15.001 geçerli etiketli satır dağılımı ve çelişkili etiketler nasıl açıklanabilir?
8. Kaynağın sabit revizyonuna bağlanan imzalı veya doğrulanabilir tarihli bir izin ve kaynak kökeni belgesi sunabilir misiniz?

## 2. Kaynak sahibine iletilmek üzere hazır talep metni

Merhaba,

dogukanvzr/ml-paraphrase-tr veri kümesini çevrimdışı çalışan, ileride ticari kullanıma sunulması planlanan bir Türkçe embedding modeli için değerlendirmekteyiz. Apache-2.0 lisans beyanınızı gördük. Ticari eğitime geçmeden önce özgün cümlelerin hangi kaynaklardan üretildiğini, başka hak sahiplerine ait metin bulunup bulunmadığını, lisans verme yetkinizi ve veriyle eğitilen model ağırlıklarının ücretli/offline dağıtımına ilişkin şartları yazılı olarak doğrulayabilir misiniz? Atıf/NOTICE gerekliliklerini ve etiketleme yönteminizi de paylaşabilirseniz memnun oluruz.

İncelediğimiz kaynak commit: b9d5707470340db13d788a338e7f7897c5e29932.

Teşekkür ederiz.

Bu metin taslaktır, herhangi bir gönderim yapılmadı.

## 3. Hak kanıtı doğrulama

Hak sahibi yanıtı, özgün kaynak listesi, varsa ticari izin ve NOTICE şartları yerel bir klasörde korunmalı. SHA-256 dosya bütünlüğü ve bağımsız hukuk incelemesi birbirinden ayrılır.

Komut: python -m scripts.faqvec_d02_rights --evidence-register HAK_KAYDI.json --output reports/faqvec-d02/rights_status.json

Kayıt şeması: source_repo, source_revision, source_sha256, creator_or_rights_holder, contact_channel, underlying_sentence_origin, third_party_text_sources, commercial_ml_training_permission, fine_tuned_weight_distribution_permission, license_obligations, independent_legal_reviewer, independent_legal_review_date, evidence_files. Evidence_files içindeki her dosyanın path ve sha256 bilgisi gerekir.

Ticari eğitim ve model dağıtım hakkı iki ayrı alanla değerlendirilir. Kod yalnızca belge ve SHA tutarlılığını kontrol eder; gerçek hak sahipliği veya imza doğruluğunu otomatik tespit edemez. commercial_training durumu bu aşamada da HOLD'dur. Kaynak belgeleri GitHub deposuna yüklenmemeli.

## 4. İki incelemecili yerel soru karşılaştırma paneli

Önce özgün kaynağı ve özel görev dosyasını üret:

    python -m scripts.fetch_faqvec_d01_original --output datasets/faqvec_d01_original
    python -m scripts.faqvec_d02_review prepare --input datasets/faqvec_d01_original/ml_paraphrase_60k_labeled.jsonl --output-dir reports/faqvec-d02

Üç çıktı: review_bundle.PRIVATE.json (ham soru metinleri; özel), frozen_candidate_test_ids.json (sabit test aday kimlikleri ve SHA), summary.json (ham soru içermeyen sayım).

İncelemeci 1 ve incelemeci 2, frontend/d02_review_offline.html dosyasını kendi tarayıcısında yerel olarak açar. Görev paketini içe alır; soru çiftlerine SAME / DIFFERENT / UNCERTAIN kararı ve gerekçe yazar. Her biri ayrı reviewer_id ile JSON dışa aktarır. İkinci kişi ilk kişinin karar dosyasını görmeden değerlendirmelidir. Sistem kurumsal kimlik doğrulaması sağlamadığından bağımsızlık süreç sorumlusu tarafından doğrulanmalıdır.

İki incelemeyi birleştir:

    python -m scripts.faqvec_d02_review aggregate --bundle reports/faqvec-d02/review_bundle.PRIVATE.json --review-a INCELEMECI_1.json --review-b INCELEMECI_2.json --output reports/faqvec-d02/dual_review_report.json

İki farklı incelemecinin aynı kararı verdiği çiftlerde yalnızca araştırma amaçlı karar kaydı açılır. Eksik, belirsiz ve anlaşmazlıklı çiftler beklemeye alınır. Negatif çiftler doğrudan onaylı zor negatif olmaz; hak kanıtı eksikken reviewed_rights_hold olarak saklanır. Çift insan kararı lisans incelemesini geçersiz kılmaz.

## 5. Sabit aday test kümesi

frozen_candidate_test_ids.json kaynak SHA, bölme sözleşmesi ve test aday niyetlerinin kilitli kimliklerini içerir. Bu veri train/validation/test niyet bölmelerinin değişmediğini doğrular. Fakat aynı kaynaktan türetilmiş test soruları, farklı müşterilerden gelen bağımsız saha testi değildir. İnsan etiketi ve gerçek müşteri destek alanı doğrulaması olmadan benchmark PASS değildir.

## 6. GitHub Actions ve gizlilik

FAQVec D02 Independent Review Preparation iş akışı özgün kaynağı sabit SHA üzerinden indirir, özel inceleme paketini CI diski üzerinde oluşturur, yalnız summary.json ve hash tabanlı test aday kimliklerini artifact olarak sunar. review_bundle.PRIVATE.json, soru metinleri ve orijinal veri dosyası yayımlanmaz.

## 7. Mühendislik durumları

Kaynak bütünlüğü: PASS (D01).
İnceleme paketinin oluşturulması: otomatik CI ile ayrıca doğrulanır.
Gerçek hak sahibinden ticari izin ve ilk kaynak belgeleri: HOLD.
Bağımsız insan etiketleme ve çelişkilerin çözülmesi: HOLD.
Bağımsız gerçek müşteri destek testi: HOLD.
E5 ince ayarı / BGE-M3 / MiniLM rekabet ölçümü: HOLD.
Ticari ürün yayını: HOLD.