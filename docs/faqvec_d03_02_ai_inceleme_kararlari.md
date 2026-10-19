# FAQVec-TR D03-02 — Yapay zekâ ile anlamsal gözden geçirme

Kullanıcı kararı: Etiketlerin yapay zekâ tarafından değerlendirilmesi kabul ediliyor; bağımsız insan incelemesi istenmiyor.

- İncelenen özgün taslak: 96 niyet, 192 alternatif, 48 farklı niyet çifti, 24 yanıtsızlık adayı.
- Niyet düzeltmesi gerektiren kayıtlar: siparis-03, kargo-05, degisim-01, urun-04, teslimat-01, teslimat-04, teslimat-07, destek-02, fatura-06, gizlilik-04, gizlilik-05.
- 48 farklı niyet çiftinin tamamı zor negatif değildir. 28'i karıştırılabilir zor negatif ADAYI, 20'si sıradan negatif.
- Yanıtsızlık adaylarından oos-kampanya-2 ve oos-teslimat-2 gerçekçi olmadığı için benchmark adayından dışlanmalı.
- Kalan 22 yanıtsızlık sorusu yalnız kurgusal FAQ galerisinde cevap bulunmaması yönünden araştırma adayıdır.
- Bu çalışma **AI değerlendirmesi** olup insan kararı, bağımsız kalite testi, veri hakları garantisi veya ticari kullanım onayı değildir.

**Karar:** AI_ÖN_İNCELEME_YAPILDI / 11_DÜZELTME_GEREKLİ / GERÇEK_MODEL_EĞİTİMİ_YAPILMADI / TİCARİ_YAYIN_HOLD.

Veri kökeni ilkesi değişmedi: yalnız özgün proje metinleri veya kökeni doğrulanmış CC0/kamu malı; önceki üçüncü taraf korpusa dönüş yok.


## Değerlendirme sonucu ve uygulanan düzeltmeler

Kaynak taslağın Git blob kimlikleri sabitlendi:

- SSS niyet kataloğu: `d82e148c8d203d3bb5732c5f64b8e2bccd757f6a`
- Yanıtsızlık kataloğu: `ba6a246ce0fda3fcd107f813600b5cd0d3da9449`

Herhangi bir kaynak metin değişirse `scripts/faqvec_d03_ai_review.py` yeniden gözden geçirme yapılmasını zorunlu tutar.

### 96 SSS niyeti

96 niyetin 192 alternatif soru ifadesi ve koşullu cevapları incelendi. **11 niyetteki belirsiz veya farklı ihtiyacı çağrıştıran ifadeler yeni AI araştırma çıktısında düzeltiliyor:** `siparis-03`, `kargo-05`, `degisim-01`, `urun-04`, `teslimat-01`, `teslimat-04`, `teslimat-07`, `destek-02`, `fatura-06`, `gizlilik-04`, `gizlilik-05`.

Diğer 85 niyet mevcut taslak içeriğiyle **AI araştırma kullanımı için uygun** değerlendirildi. Bu inceleme kendi oluşturduğumuz kurgusal metinleri kapsar; başka firmaların gerçek operasyon politikalarını doğrulamaz.

### 48 farklı niyet çifti

Her iki soru gerçekten farklı cevap gerektirecek şekilde tasarlanmıştır. Bununla birlikte her farklı niyet çiftini *hard negative* saymak metodolojik açıdan yanlıştır.

- **28 olası zor negatif:** siparis-grup-{1,2,3}, kargo-grup-{1,2,3}, iade-grup-{1,2,3}, degisim-grup-1, odeme-grup-{1,3}, uyelik-grup-{1,4}, kampanya-grup-{1,2}, urun-grup-{1,2,3}, teslimat-grup-{1,3,4}, destek-grup-{1,2}, fatura-grup-{2,3}, gizlilik-grup-{1,3}.
- **20 sıradan negatif:** Bunların dışında kalan iki niyetli aileler; farklı cevap gerektirir, ancak güçlü karışma riski taşıdığı kanıtlanmadığından zor negatif eğitim havuzuna alınmaz.

Zor negatif sınıflaması AI'nın semantik değerlendirmesidir; gerçek E5/BGE/MiniLM yakınlık skoruyla henüz doğrulanmadı. Yalnız eğitim bölmesindeki AI-negatifler araştırma amacıyla kullanılabilir.

### 24 yanıtsızlık örneği

22 tanesi örnek SSS galerisinin cevap kapsamı dışında değerlendirildi. `oos-kampanya-2` (kuponla döviz kurunu değiştirmek) ve `oos-teslimat-2` (gelecekteki trafik kazalarını kesin bilmek) gerçekçi kullanıcı sorguları olmadığından **benchmark havuzundan çıkarılıyor**. Kalan sorguların bir kısmı başkalarına ait özel veri istemektedir; bu tür durumlarda sistem gerçek bilgi üretmek yerine güvenli reddetme veya uygun destek kanalına yönlendirme yapmalıdır. Bunlar **sessiz kalınması** anlamına gelmez.

## Kullanım yolu

```powershell
.venv\Scripts\python.exe -m scripts.faqvec_d03_ai_review --check-only
.venv\Scripts\python.exe -m scripts.faqvec_d03_ai_review --output-dir datasets/faqvec_ai_review_v02
```

İkinci komut eski özgün taslağı değiştirmeden dört kayıt dosyası üretir: `faq.AI_RESEARCH.jsonl`, `positive_ai_review.jsonl`, `negative_ai_review.jsonl`, `no_answer_ai_review.jsonl`. Her biri SHA-256 dosya özetleriyle `manifest.AI_RESEARCH_ONLY.json` içinde izlenir.

**İsteğe bağlı ve yalnız araştırma için E5 fine-tune:**

```powershell
.venv\Scripts\python.exe -m scripts.train_faqvec_v2 --ai-owned-research --backbone models/e5-base-original --epochs 2 --batch-size 2 --gradient-accumulation 8 --output models/faqvec-tr-ai-research
```

İstenirse aynı komuta `--include-ai-negatives` eklenerek yalnız eğitim bölümüne ait olası zor negatifler araştırmaya katılabilir. Komutun çalışabilmesi için önceden yerelde bulunan uygun lisanslı E5-base ağırlıkları ve eğitim bağımlılıkları gerekir; model ağırlıkları bu aşamada indirilmedi. `--ai-owned-research` ile `--commercial` birlikte kullanılamaz.

**Sınır:** Kullanıcının insan incelemesinden vazgeçmesi, AI kararlarını iki bağımsız insanın kararı yapmaz. Yapay zekâ tarafından oluşturulan ve yine yapay zekâ tarafından kontrol edilen soruların sonuçları bağımsız model değerlendirmesi sayılamaz. Ticari yayın ve gerçek dünya performansı hâlâ HOLD.
