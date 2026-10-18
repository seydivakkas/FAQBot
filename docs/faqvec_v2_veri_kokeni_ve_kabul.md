# FAQVec-TR — Türkçe Veri Kökeni ve Bağımsız Kabul Kaydı

Durum: 18 Ekim 2026 — VERİ HAKLARI HOLD / UZMAN ETİKETLERİ HOLD / GERÇEK E5 MODEL KABULÜ HOLD.

## Araştırılan veri kaynakları

| Kaynak | Kart beyanı | Miktar | Uygunluk | Karar |
| --- | --- | --- | --- | --- |
| https://huggingface.co/datasets/dogukanvzr/ml-paraphrase-tr | Apache-2.0 | 60.000 Türkçe çift; 45.000 pozitif, 15.000 rastgele negatif | Genel ML/teknik metin, müşteri desteği değildir | ADAY: bağımsız köken/lisans ve örnek etiket denetimi gerekir |
| https://huggingface.co/datasets/yunus-emre/tr-legal-triplets | Apache-2.0 | Yaklaşık 1,15 milyon hukuk üçlüsü | Hukuk alanı; e-ticaret ihtiyacını temsil etmez | KARANTİNA: içerik, kaynak hakları ve alan kayması ayrıca incelenecek |
| https://huggingface.co/datasets/erenyanic/sts-tr-dataset | CC BY-SA 4.0, haber RSS kaynakları da var | 81 puanlı çift | Bağımsız STS analizi açısından küçük | TİCARİ EĞİTİME KATMA: yeniden dağıtım ve haber telifi denetimi açık |
| https://huggingface.co/datasets/menesnas/SemanticTextualSimilarityDataset | MIT beyanı | 50 manuel puanlı çift | Genel STS kontrolüne aday | BAĞIMSIZ KÖKEN ve ETİKET DENETİMİ AÇIK |

HF veri kartındaki lisans beyanı **tek başına temel metinlerin hak sahipliği veya eğitime izin kanıtı değildir**. Kaynak veri kökeni, revizyon SHA, kaynak lisans metni, atıf ve örneklerin üretim süreci manuel teyit edilmeden commercial_training_approved=true işaretlenmemelidir.

## İlk teslim — hazırlama altyapısı

1. Kaynağı yalnızca istenirse indirin: python -m scripts.fetch_faqvec_v2_pairs --output datasets/faqvec_raw_paraphrase_tr
2. Bu işlem Hugging Face dataset kartı lisans beyanını Apache-2.0 olarak kontrol eder, commit SHA ve indirilen dosyaların SHA-256 özetlerini kaydeder. İnternet sadece burada gerekir.
3. İndirilen JSON/JSONL/Parquet dosyalarından birini seçip dönüştürün:
   python -m scripts.prepare_faqvec_v2_pairs --source-file datasets/faqvec_raw_paraphrase_tr/ORIGINAL_DATA.json --card-path datasets/faqvec_raw_paraphrase_tr/README.md --revision GERCEK_HF_COMMIT_SHA --output reports/faqvec_v2_pairs
4. İşlem normalize edilmiş **pozitif** çiftleri bağlantılı bileşenlere ayırır; tüm paraphrase ifadeleri aynı intent_id/split içinde tutulur. Karşıt etiketli çiftler ve pozitif kümeye düşen negatifler işlemi durdurur; aşırı büyük bileşenler karantinaya alınır.
5. Rastgele negatifler ayrı negative_candidates_unreviewed.jsonl dosyasına **needs_human_review** statüsüyle yazılır; eğitime onaylı zor negatif olarak otomatik sokulmaz.
6. manifest.CANDIDATE.json commercial_training_approved=false ile üretilir. Başka kişi incelemeden true yapılmaz.

**Not:** Harici kaynakta 60.000 satır bulunduğu beyan edilmesi, 60.000 kullanılabilir ve bağımsız niyet çıktığı anlamına gelmez. Gerçek indirmenin ardından kabul edilen/karantinaya alınan/dışlanan çift sayıları SHA'lı raporla belirlenmelidir. Bu ortamda harici ağırlık veya veri dosyaları indirilmedi.

## İnsan inceleme kuralları

- Pozitif: İki cümle aynı cevabı gerektiriyor mu? Evet/Hayır/Kararsız.
- Zor negatif: Benzer konu veya sözcüklere rağmen farklı cevap gerektiriyor mu? Evet/Hayır/Kararsız.
- OOS/no-answer: Mevcut SSS bilgi tabanında kesin cevap olmamalı mı? Evet/Hayır/Kararsız.
- Her onaylı kayıt için bağımsız kontrol yapan reviewer kimliği, karar tarihi, gerekçe, veri kaynağı ve orijinal kayıt ID tutulmalı.
- Çelişkili veya kararsız kayıtlar eğitim/teste alınmamalı.
- Gerçek müşteri mesajları izin/onay ve kişisel veri temizleme tamamlanmadan toplanmamalı.

## Deney sözleşmesi

1. Train, validation ve test niyet düzeyinde ve kaynak bazlı ayrılır. Aynı veya normalizasyonla benzer metnin çapraz bölmede bulunması engellenir.
2. Önce dokunulmamış MIT E5-base, TF-IDF, MiniLM, MIT BGE-M3 aynı soru galerisiyle test edilir.
3. FAQVec-TR v0.2 eğitimi yalnızca doğrulanmış train çiftleriyle yapılır; validation sadece eşik/hiperparametre seçimine ayrılır.
4. Test verisinde Recall@1, Recall@5, yanlış eşleşme, pozitif yanıtsız bırakma, OOS yanlış cevap ve OOS doğru fallback ayrı hesaplanır.
5. Yöntemlerin farklı skor dağılımları yüzünden tek ortak yüzde eşiği dayatılmaz. Her yöntem için eşik validation üzerinde ayrı kalibre edilir, testte sabit tutulur.
6. Model başına latency p50/p95, throughput, RAM değişimi, CUDA peak VRAM ve model klasörü boyutu Windows/RTX 4070 üzerinde raporlanır.
7. Rakiplerine göre farklar için niyet kümelerini birim alan eşleştirilmiş bootstrap %95 güven aralığı kullanılır. Küçük veya aynı veriyle hazırlanmış testler ticari kabul sayılmaz.

## Ticari PASS kapıları

- Kaynak hakları ve üçüncü taraf NOTICE/SBOM kapalı değilse MODEL KABULÜ HOLD.
- Uzman tarafından onaylanan e-ticaret soru çeşitliliği ve bağımsız OOS seti yoksa MODEL KABULÜ HOLD.
- FAQVec-TR v0.2'nin E5 ve TF-IDF karşısında Recall@1 iyileşmesi gösterilmeli; yanlış cevap ve OOS oranları kötüleşmemeli.
- BGE-M3 gibi daha büyük modeller karşısında kalite–gecikme–RAM/VRAM–paket boyutu dengesi değerlendirilir; her alanda lider olması şart değildir.
- CPU ve Windows offline .exe gerçek kabulüne kadar ticari dağıtım HOLD.

Bu belge kaynak kartlarını bulmanın ve teknik aktarımın yapıldığını, **hak doğrulaması veya gerçek 60K veri üzerinde eğitim yapıldığını değil**, kayıt altına alır.
