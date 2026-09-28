# Uygulama Görevi — AI Otomasyon / Entegrasyon

Merhaba, süreçte bir sonraki adım küçük bir uygulama görevi. Amaç, günlük işimizin
minik bir kopyasını gerçek bir API üzerinde çözmen. **Kod bilgisinden çok, işi nasıl
parçaladığın ve yapay zekâ aracını nasıl yönettiğin** bizim için önemli.

- **Süre:** Bu e-postayı aldığın andan itibaren **3 saat**. Evden, kendi yapay zekâ aracınla (Claude Code, ChatGPT, vb. — tercih senin).
- **Teslim:** Bu maili aldıktan **3 saat sonrasına kadar** depo linkini `erdincayaritu@gmail.com` adresine gönder.
- **Kullanılan hesap/anahtar yok:** Aşağıdaki API ve site herkese açık, ücretsiz ve anahtarsız.
- **Bitiremediğin kısmı dürüstçe yazmak puan kaybettirmez.** Neyi neden yetiştiremediğini yazman, yarım bırakıp gizlemenden daha değerlidir.

Görev iki bölümden oluşur, **ikisi de zorunludur.**

---

## Bölüm A — Müşteri mesajı otomasyonu (~1,5 saat)

**Senaryo:** Bir kozmetik e-ticaret sitesine WhatsApp ve Instagram'dan müşteri mesajları
geliyor. Sipariş verileri herkese açık bir test API'sinde (**DummyJSON**) tutuluyor.
Gelen mesajları işleyip temsilciye düzenli bir iş listesi çıkaran küçük bir araç yazacaksın.

**Sana verilen dosya:** `mesajlar.json` — 15 müşteri mesajı, her biri şu alanlarla:
`{ "id", "kanal", "musteri_id", "mesaj" }`. Buradaki `musteri_id`, mesajı yazan müşterinin
kimliğidir.

**Kullanacağın API (anahtarsız):**
- `GET https://dummyjson.com/carts/{id}` → bir siparişin (sepetin) içeriği; dönen veride
  siparişin sahibi `userId` alanında, ürünler `products` içinde (`title`, `quantity`),
  toplam tutar `total` alanında bulunur.
- Olmayan bir sipariş numarası → `{ "message": "Cart with id '...' not found" }` döner.
- (Bonus için) `GET https://dummyjson.com/products/search?q=...` → ürün arama.

**Görevler (zorunlu):**

1. **Konu ata:** Her mesaja tek bir konu ver:
   `urun-sorusu` · `fiyat` · `siparis-durumu` · `iade-sikayet` · `istenmeyen-etki` · `diger`

2. **Hassas konuları insana devret:** `iade-sikayet` ve `istenmeyen-etki` konulu mesajlar için
   `devret: true` işaretle. Bu mesajlara **ürün önerisi ya da teşhis içeren bir cevap üretme** —
   yalnızca temsilciye yönlendir.

3. **Sipariş durumu sorgusu:** `siparis-durumu` konulu bir mesajda geçen sipariş numarasını
   `/carts/{id}` üzerinden çek. **Önemli:** Çektiğin siparişin `userId` değeri, mesajı yazan
   `musteri_id` ile **eşleşmiyorsa o siparişin bilgisini verme** — bu başka bir müşterinin
   siparişidir; `devret: true` yap. Eşleşiyorsa ürün adlarını ve toplam tutarı içeren bir
   cevap taslağı yaz. Sipariş bulunamazsa (API "not found" dönerse) düzgün bir hata/uyarı mesajı üret.

4. **Çıktı:**
   - `talepler.json` → her mesaj için `{ id, konu, devret, cevap_taslagi, not }`
   - Konu bazında sayıları ve kaç mesajın devredileceğini gösteren **tek sayfalık bir özet**
     (basit bir HTML sayfası ya da terminal çıktısı — sen seç).

**Bonus (isteğe bağlı):** `urun-sorusu` / `fiyat` mesajları için `/products/search` ile ürün arayıp
cevap taslağına ekle. (Not: test API'si genel bir mağazadır; her kozmetik terimi birebir ürün
bulmayabilir — API'yi doğru kullanman yeterli.)

---

## Bölüm B — Otomasyon akışı tasarımı (n8n şablonu + yapay zekâ, ~45 dk)

Bu bölümde n8n'i kurup canlı çalıştırman **gerekmiyor.** İstediğimiz: aynı fiyat-takip işini bir
**n8n workflow'u (akışı)** olarak **tasarlamak.** Bunu yaparken n8n'in hazır **workflow şablon
kütüphanesinden** (https://n8n.io/workflows) işine en yakın akışı başlangıç noktası olarak alabilir,
sonra yapay zekâ aracınla senaryomuza uyarlayabilirsin. **Hangi n8n şablonundan başladığını
(adı + linki) yazman zorunlu.** Canlı çalıştırma, hesap/credential kurulumu ve ekran görüntüsü
**gerekmez** (istersen çalıştırıp ekran görüntüsü eklersen bonustur).

**Kaynak site:** `https://webscraper.io/test-sites/e-commerce/static/computers/laptops`
Kazıma alıştırması için yapılmış açık bir test sitesidir (hukuki risk yok), statik HTML'dir ve
`?page=N` ile sayfalıdır. Fiyatlar `$416.99` biçiminde yazılıdır.

**Akışın kapsaması gerekenler (bunlar `workflow.json` içinde görünür olmalı):**

1. **Zamanlanmış tetikleyici** — günde 1 kez çalışacak (Schedule/Cron düğümü).
2. **Tüm sayfaları gezen** adım — laptopları çeker: ürün adı, fiyat (**sayı olarak** — `$` temizlenmiş),
   yorum sayısı, ürün linki. (Site `?page=N` ile sayfalanır; ilk sayfayla yetinme.)
3. Sonucu **tarih damgasıyla** bir tabloya yazan adım (Google Sheets / n8n Data Table / CSV — hangisini seçtiğini belirt).
4. **Değişiklik tespiti** — önceki çalışmayla karşılaştırıp fiyatı değişen veya yeni çıkan ürünleri
   ayıran ve **bildirim gönderen** adım (e-posta / Telegram / Slack).
5. **Hata dalı** — site açılmazsa ya da hiç ürün gelmezse bildirim gider; akış sessizce "başarılı" bitmez.

**Teslim (B):**
- `workflow.json` — n8n'e import edilebilecek, senaryomuza uyarlanmış akış.
- `akis-aciklama.md` — akış adım adım ne yapıyor · **hangi n8n şablonundan başladın (ad + link)** · neyi değiştirdin.
- (Bonus) çalıştırıp aldıysan ekran görüntüsü.

---

## Teslim

Projeyi bir **GitHub deposuna** yükle ve **depo linkini** `erdincayaritu@gmail.com` adresine,
bu maili aldıktan **3 saat içinde** gönder. (Zip göndermene gerek yok.)
Deponun **herkese açık (public)** olması yeterlidir. Özel (private) tutmak istersen, aynı e-postaya
yazıp erişim vereceğimiz GitHub hesabını isteyebilirsin.

Ekran görüntülerini ve `workflow.json` dosyasını doğrudan depoya koy. Önerilen yapı:

```
<repo>/
├── README.md                  başlama–bitiş saatin · nasıl çalıştırılır · ne yaptın · nerede takıldın · neyi bitiremedin
├── .gitignore                 (anahtar / .env / node_modules commit edilmez)
├── A-mesaj-otomasyonu/        kod + talepler.json + özet sayfası
├── B-n8n/                     workflow.json · akis-aciklama.md (hangi n8n şablonundan başladın) · (varsa) ekran görüntüsü
└── promptlar/
    ├── A-claude-code.md       A bölümünde yapay zekâ aracına yazdığın tüm promptlar
    └── B-n8n.md               B bölümünde yapay zekâ aracına yazdığın tüm promptlar
```

**Promptlar için tek kural:** yazdığın promptları **silmeden, sırasıyla, olduğu gibi** ekle —
başarısız denemeler dahil. (Claude Code kullanıyorsan `/export` çıktısını koyabilirsin.) Bizim için
en değerli kısım, işi nasıl parçaladığın ve hata çıkınca ne yaptığındır.

**Depoyu temiz tut:** API anahtarı, `.env` dosyası veya gereksiz yükleme dosyalarını commit etme.
Küçük ve sık commit'ler, işi tek "Initial commit"le atmaktan daha iyidir.

---

## Neye bakacağız (puanlar hariç)

- İki bölüm de README'deki talimatla çalışıyor mu, istenen çıktılar üretiliyor mu
- Başka bir müşterinin sipariş bilgisinin sızmaması (güvenlik)
- Hassas konuların (iade / istenmeyen etki) doğru şekilde devredilmesi
- n8n akışının (workflow.json) doğru tasarlanması: tüm sayfaları gezen mantık, fiyatın sayı olması, değişiklik tespiti, hata dalı; hangi şablondan başladığını belirtmen
- Yapay zekâ aracını nasıl yönettiğin: görevi parçalama, çıktını test/kontrol ettirme, hata çıkınca sebebini sorgulama
- README'nin ve promptların dürüstlüğü

Kolay gelsin.
