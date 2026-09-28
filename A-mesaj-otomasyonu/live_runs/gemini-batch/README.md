# Canlı Gemini Kanıtı (eski şema)

Bu klasör, gerçek Gemini API entegrasyonunun çalıştığını gösteren **kanıt** amaçlı bir çıktıdır.
Teslim edilen sonuç değildir; teslim edilen çıktı `A-mesaj-otomasyonu/talepler.json` dosyasıdır.

- Tarih: 28 Eylül 2026, 12:38 (Europe/Istanbul). Model: `gemini-2.5-flash-lite`. 15 mesaj tek batch isteğinde gönderildi.
- Bu çalıştırmada kullanılan prompt ve şema **eskidir**:
  - Prompt zero-shot'tı; sonradan few-shot'a çevrildi.
  - `istenmeyen_mesaj` konusu henüz yoktu. Bu yüzden 7. mesaj `diger` olarak görünür, spam bilgisi o zamanki `is_spam` alanındaydı.
  - Kanal bazlı özet satırları yoktur.
- Konu ve devir kararları, o günkü referansla 15/15 aynıydı.
- Güncel prompt ve şemayla canlı çalıştırma yapılmadı.
