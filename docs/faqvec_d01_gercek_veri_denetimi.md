> **ARŞİV — BU YOL ARTIK KULLANILMAYACAK.** Kullanıcının kesin veri politikası gereği üçüncü taraf `dogukanvzr/ml-paraphrase-tr` veri kümesi indirilmeyecek, işlenmeyecek, eğitimde veya karşılaştırmada kullanılmayacak. Önceki kaynak sayımları yalnız geçmiş teknik kayıtlarıdır. Yeni çalışma: [yalnız OWNED / doğrulanmış CC0](VERI_KAYNAGI_KESIN_POLITIKA.md). Kaynak yayıncısından izin isteme planı iptal edilmiştir.

# FAQVec-TR-V2-D01 — Özgün 60K Dosya Denetimi (18 Ekim 2026)

## Kaynak ve hash kanıtı

- Veri: https://huggingface.co/datasets/dogukanvzr/ml-paraphrase-tr
- Orijinal dosya: ml_paraphrase_60k_labeled.jsonl
- Sabit kaynak revizyonu: b9d5707470340db13d788a338e7f7897c5e29932
- Orijinal dosya boyutu: 16.459.390 bayt
- Orijinal JSONL SHA-256: 2c5bace5f34bbc9bc79084ddf57bc5a298310eaa2614beb9f7862a16b674e39d
- Kaynak kartı README.md SHA-256: 825475054d18d296186f31546a375eb7061fced641c13ad8b53c3776a554524f
- Gerçek GitHub Actions koşusu: https://github.com/seydivakkas/FAQBot/actions/runs/39131287668
- Kanıt paketi: GitHub Actions artifact faqvec-d01-counts-provenance, 30 gün saklama; ham JSONL bu pakette bulunmaz.

Orijinal dosya sabit Hugging Face revizyonundan indirildi; SHA-256 Hugging Face LFS OID değeriyle birebir eşleşti. Fiziksel bütünlük PASS. Bu sonuç cümlelerin özgün yazarlık veya kullanım hakkını kanıtlamaz.

## Gerçek dosyanın satır ve karantina envanteri

| Kalem | Sayı |
| --- | ---: |
| Özgün JSONL satırları | 60.000 |
| Geçerli biçim/normalizasyon satırları | 59.996 |
| Pozitif etiketli geçerli satırlar | 44.995 |
| Negatif etiketli geçerli satırlar | 15.001 |
| Normalizasyon sonrası aynı cümle çiftleri | 4 |
| Yinelenen aynı etiketli satırlar | 241 |
| Normalleştirilmiş benzersiz çiftler | 59.754 |
| Her iki etiketle işaretlenen farklı çift | 1 |
| Benzersiz normalize cümleler | 84.008 |
| Çelişkisiz benzersiz pozitif çiftler | 44.753 |
| Çelişkisiz benzersiz negatif çiftler | 15.000 |
| En az iki ifadeli pozitif bağlantı bileşenleri | 39.303 |
| 25 ifadeden büyük kümeler | 27 |
| Etiket çelişkisi bulunan kümeler | 3 |
| Toplam farklı karantina kümeleri | 29 |
| Karantinaya düşen pozitif çiftler | 1.608 |
| **İnsan incelemesine aday pozitif çiftler** | **43.145** |
| **İnsan incelemesine aday niyet kümeleri** | **39.276** |
| Pozitif kümeye düşen açık negatif çift | 1 |
| **İnsan incelemesine aday negatif çiftler** | **13.813** |
| Aday dışındaki negatif çiftler | 1.187 |
| Ticari eğitim için bağımsız onaylı pozitif çift | **0** |
| İnsan onaylı zor negatif çift | **0** |

27 büyük ve 3 çelişkili kümenin kesişimi olduğundan farklı karantina kümesi 29'dur.

Aday niyetlerin hash temelli bölmeleri:

| Bölme | Niyet adayı |
| --- | ---: |
| Train | 27.569 |
| Validation | 5.862 |
| Test | 5.845 |
| Toplam | 39.276 |

39.276 niyet ve 43.145 pozitif çift yalnızca otomatik yapısal kontrolden geçmiş adaydır. İnsan tarafından anlamsal doğruluğu teyit edilmedi. 13.813 negatif çift de henüz zor negatif sayılmaz ve eğitime sokulmaz. Bu bölmeler bağımsız müşteri destek testi değildir.

## Hak zinciri

Dataset kartında Apache-2.0 beyanı vardır; kart toplam 45.000 pozitif / 15.000 rastgele negatif çift iddia eder. Gerçek dosyada geçerli çiftlerin etiket sayıları 44.995 ve 15.001 olarak ölçüldü. Kaynak kartı, temel cümlelerin kimden geldiğine ve üçüncü taraf alıntı bulunmadığına ilişkin bağımsız hak belgesi sunmuyor. İzin kapsamı, ilk kaynak, varsa alıntılar ve ticari model ağırlıklarını dağıtım hakkı ayrı inceleme gerektirir. Karttaki lisans beyanı tek başına bağımsız hukuki onay değildir.

## Son mühendislik kararı

ÖZGÜN_DOSYA_SHA_PASS / SATIR_ENVANTERİ_PASS / ANLAMSAL_ETİKET_KABULÜ_HOLD / VERİ_HAKLARI_HOLD / TİCARİ_EĞİTİM_HOLD / E5_MODEL_KABULÜ_HOLD

## D02'ye aktarılan kapılar

1. Veri oluşturucusundan veya özgün belgelerden ilk cümle kaynaklarını ve ticari eğitim kullanım hakkını doğrula.
2. Şüpheli/uzun pozitif bağlantı kümeleri ile karşıt etiketleri iki bağımsız gözle incele.
3. 13.813 negatif adaydan sözcüksel ve anlamsal bakımdan yakın olanlarını sırala. Bağımsız onaylanmadan hiçbirini gerçek zor negatif olarak etiketleme.
4. Gerçek kullanıcı/SSS cevapları için ayrıca lisanslı, mahremiyeti temizlenmiş, bağımsız domain test kümesi oluştur.
5. Yalnızca onaylanan veriyle E5-base türevi FAQVec-TR ince ayarını, ardından TF-IDF, özgün E5, BGE-M3 ve MiniLM'e karşı aynı testte değerlendir.
6. Windows CPU/GPU p50/p95, bellek, VRAM, paket boyutu, offline kabulü ve NOTICE/SBOM tamamlanana kadar ticari yayın HOLD.

Yeniden çalıştırma:

    python -m scripts.fetch_faqvec_d01_original --output datasets/faqvec_d01_original
    python -m scripts.audit_faqvec_d01 --input datasets/faqvec_d01_original/ml_paraphrase_60k_labeled.jsonl --source-card datasets/faqvec_d01_original/README.md --output-dir reports/faqvec-d01

İlk komut açık internetle kaynağı bir kez alır. İkinci komut internet olmadan yerel JSONL'yi inceler. Bu aşamada E5/BGE ağırlıkları indirip model eğitimi yapılmadı.
