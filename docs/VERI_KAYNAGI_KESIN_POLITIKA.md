# FAQBot / FAQVec-TR — Kesin Veri Kaynağı Politikası

## Bağlayıcı karar

FAQVec-TR'nin eğitim, ince ayar, zor negatif üretimi ve kabul verilerinde **yalnızca** şu kaynaklar kullanılabilir:

1. **Özgün kendi üretimimiz (OWNED):** Sıfırdan yazılmış veya izinli katkılarla oluşturulmuş; başkasının eserinden kopyalanmamış; kişisel veri/üçüncü taraf hakları barındırmayan; üretim yöntemi ve kayıt tarihi belgelenmiş soru/cevap çiftleri.
2. **Gerçekten telifsiz ve özgün kökeni doğrulanmış kamu malı / CC0-1.0:** CC0 beyanının doğru hak sahibi tarafından verildiği veya geçerli kamu malı statüsü, özgün metin kaynağı ve üçüncü taraf hak engeli doğrulanmış veriler.

**YASAK / otomatik ret:** Sadece veri kartındaki MIT, Apache-2.0, BSD, CC-BY veya başka bir açık lisans etiketine dayanarak dış veri kümesini eğitimde kullanmak; hak kökeni belirsiz üçüncü taraf metinleri indirmek/işlemek; rızasız sohbet kayıtları; internetteki paragrafları kopyalayarak özgün gibi göstermek; lisans beyanı olmayan derlemeler; dış veri indirme görevlerini otomatik CI ile çalıştırmak.

Açık kaynak yazılım ve açık ağırlıklar **eğitim verisinden farklıdır**. Uygun lisanslı ticari kullanıma açık açık kaynak model ağırlıkları (MIT, Apache-2.0 gibi), lisans ve NOTICE koşulları ayrıca karşılanarak aday olarak değerlendirilebilir. Açık model ağırlıkları için “telifsiz” veya “kendi yazdığımız özgün ağırlıklar” iddiası yapılmaz.

## D01 / D02 tarihçesinin statüsü

- `dogukanvzr/ml-paraphrase-tr` adlı üçüncü taraf kaynağı geçmişte yalnızca **GitHub Actions geçici çalışma ortamında indirildi ve teknik olarak sayıldı**. Herhangi bir hak satın alınmadı, yazılı özel izin edinilmedi ve bu verilerle FAQVec-TR'nin ticari E5 ince ayarı yapılmadı.
- Geçmiş denetim istatistikleri ve kaynak revizyonu, olayın kayıtlarını korumak için tarihî raporlarda durabilir; bunlar **kullanım onayı değildir**.
- D01/D02'nin otomatik GitHub Actions üçüncü taraf veri indirme adımları devre dışı; repo varsayılan dalındaki veri indirme komutları engellendi; D02 Windows aracı artık dış veri indirmez.
- Geçmiş commit geçmişi veya süresi dolmamış GitHub Actions artifact'ları bu değişiklikle geriye dönük silinmiş değildir. Kullanıcı yerel bilgisayarında ayrıca indirme yaptıysa bu düzenleme yerel dosyaları da silmez. Ham veriler hiçbir yeni eğitim/benchmark akışına sokulmamalıdır.

## Her yeni veri kümesi için zorunlu kontrol

- `source_id`, veri kökeni, özgün yazar veya oluşturucu, lisans (`OWNED` / `CC0-1.0`) ve doğrulanabilir köken kanıtı yer almalı.
- Kullanılacak gerçek veri dosyalarının SHA-256 hash değerleri, sürümü ve eğitim/test ayrımı kayıt altına alınmalı.
- Üçüncü taraf CC0 kaynağı için **kart üstündeki CC0 etiketi tek başına yeterli değildir**; asıl içerik kökeni ve hak sahipliği doğrulanmalı.
- Eğitimde aynı intent farklı bölmelere taşınmamalı; pozitif/negatif etiketler ayrıca insan kontrolünden geçmeli.
- Kabul doğrulamaları ve model kıyaslamaları yalnız kabul edilmiş kaynaklardan oluşturulmuş veriyle yapılmalı.
- Belge/özgünlük belirsizse varsayılan karar **HOLD**; sürecin sonraki adımları çalışmamalı.

## Geliştirme ajanları için ilke

Bu dosya bütün gelecek FAQBot işlemlerinin temelidir. Yeni kod, veri indirme, test ve CI değişiklikleri bu sözleşmeyi gevşetemez. İlk ilke: **KENDİ_VERİMİZ_VEYA_DOĞRULANMIŞ_CC0 / HARİCİ_BELİRSİZ_VERİ_YASAK**.
