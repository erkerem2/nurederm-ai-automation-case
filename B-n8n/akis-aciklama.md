# Bölüm B — Laptop Fiyat Takibi (n8n)

`workflow.json`, webscraper.io test sitesindeki bütün laptop sayfalarını günde bir kez
tarar. Sonuçları tarih damgasıyla Google Sheets'e yazar, önceki çalışmayla
karşılaştırır ve yeni ürün ile fiyat değişikliklerini Telegram'dan bildirir.
Tarama başarısız olursa ya da eksik kalırsa hata bildirimi gönderilir ve
execution başarısız olarak işaretlenir.

## Başlangıç şablonu

- **Ad:** Competitor price monitoring with web scraping, Google Sheets & Telegram (hazırlayan: Tony Paul)
- **Link:** https://n8n.io/workflows/4640-competitor-price-monitoring-with-web-scrapinggoogle-sheets-and-telegram/

Şablonun JSON'u n8n şablon API'sinden (`api.n8n.io/api/templates/workflows/4640`)
indirildi ve düğüm düğüm incelendi. `workflow.json` içinde `meta.templateId: "4640"`
olarak da kayıtlı.

## Akış adım adım

| # | Düğüm | Ne yapar |
| --- | --- | --- |
| 1 | **Daily 09:00 Trigger** (Schedule) | Her gün 09:00'da çalışır. Workflow saat dilimi `Europe/Istanbul`. |
| 1 | **Manual Test Trigger** | Aynı akışı elle test etmek için. |
| 2 | **Fetch All Pages** (Code) | `.../computers/laptops` ile başlar ve sayfadaki `rel="next"` bağlantısını bitene kadar takip eder (`?page=2`, `?page=3` …). Sayfa sayısı koda yazılmadı. Döngü tespiti, 100 sayfalık güvenlik sınırı ve istekler arasında 0,5 sn bekleme var. |
| 2 | **Parse Products** (Code) | Her ürün kartından `name`, `price` (`$1,139.54` → `1139.54`, **sayı**), `price_cents`, `review_count` (sayı) ve mutlak `product_url` alanlarını çıkarır. Eksik alan, boş sayfa veya sitedeki "N items" toplamıyla tutmayan ürün sayısı hata sayılır. |
| 3 | **Read Latest Prices** (Google Sheets) | `latest_prices` sayfasını okur. Bu sayfa önceki tamamlanmış çalışmayı tutar. İlk çalışmada sayfa boştur. |
| 4 | **Detect Changes** (Code) | Ürünleri URL anahtarıyla eşleştirir ve her ürünü `baseline` / `new` / `price_up` / `price_down` / `unchanged` olarak etiketler. Kayan nokta hatası ve sheet'in yerel sayı formatı yanlış değişiklik üretmesin diye karşılaştırma cent cinsinden yapılır. |
| 3 | **Append Price History** (Google Sheets) | Çalışmadaki bütün ürünleri `scraped_at` tarih damgası, değişiklik tipi ve önceki fiyatla birlikte `price_history` sayfasına ekler. |
| 4 | **Build Change Summary** → **Has Changes?** → **Send Change Alert** (Telegram) | Bütün değişiklikler **tek** mesajda toplanır (en fazla 30 satır, kalanı sayı olarak). Değişiklik yoksa bildirim gönderilmez. İlk çalışmada 117 ayrı "yeni ürün" mesajı yerine tek bir başlangıç özeti gider. |
| — | **Restore Product Rows** → **Update Latest Prices** (Google Sheets) | `latest_prices` sayfasını `product_url` eşleşmesiyle günceller (append or update). Bu adım **bildirimden sonra** çalışır. Telegram gönderimi başarısız olursa referans ilerlemez ve aynı değişiklik bir sonraki çalışmada yeniden bildirilir. |
| 5 | **Build Error Alert** → **Send Error Alert** (Telegram) → **Mark Execution Failed** (Stop and Error) | Hata dalı. Bu dala Fetch, Parse, Sheets okuma/yazma, değişiklik hesaplama ve Telegram adımlarının hepsinin error output'u bağlı. Kaç hatalı item gelirse gelsin tek bir hata mesajı gönderilir. Execution sonunda **Stop and Error** ile "failed" biter, yani akış sessizce "başarılı" görünmez. |

### Hata senaryoları

- **Site açılmıyor / HTTP hatası / timeout** (ilk veya ara sayfa): `Fetch All Pages` hata verir. Hata dalı çalışır ve hiçbir tabloya yazılmaz.
- **Hiç ürün gelmiyor, sayfa boş ya da HTML yapısı değişmiş:** `Parse Products` hata verir. Eksik veri, yarım bir tarama olarak kaydedilmez.
- **Eksik tarama** (toplanan ürün sayısı sitenin ilan ettiği toplamdan az): hata sayılır.
- **Google Sheets veya Telegram hatası:** ilgili düğümün error output'u hata dalına gider.
- **Hata bildiriminin kendisi gönderilemezse** (örneğin Telegram çalışmıyorsa): execution yine başarısız olur ve n8n *Executions* ekranında görünür. İstenirse n8n'in *Error Workflow* ayarıyla ikinci bir kanal eklenebilir; bu teslimde eklenmedi.

## Şablona göre neleri değiştirdim

| Şablon (#4640) | Bu akış | Neden |
| --- | --- | --- |
| İzlenecek ürün URL'leri elle doldurulmuş bir sheet'ten okunuyor | Ürünler, kategorinin **tüm sayfaları** gezilerek keşfediliyor | Görev tüm laptopları ve yeni çıkan ürünleri istiyor |
| Ürün başına HTTP isteği + 20 sn bekleme | Sayfa başına bir istek (20 sayfa) ve 0,5 sn bekleme | Liste sayfası bütün alanları zaten içeriyor |
| HTML düğümünde tek CSS seçiciyle yalnızca fiyat | Code düğümünde ad, fiyat, yorum sayısı ve link; alan doğrulaması ve toplam sayı kontrolü | Görev dört alanı istiyor; eksik veri sessizce geçmemeli |
| `parseFloat` sonucu `!==` ile karşılaştırılıyor, `NaN` durumu kontrol edilmiyor | Fiyat format kontrolünden geçiyor, karşılaştırma tam sayı cent ile yapılıyor | Yanlış pozitif ve `NaN` riskini kaldırmak için |
| Yeni ürün kavramı yok | `new` / `price_up` / `price_down` ayrımı var, ilk çalışma `baseline` | Görevin 4. maddesi |
| Değişen her ürün için ayrı Telegram mesajı | Tek toplu mesaj; değişiklik yoksa mesaj yok | Bildirim gürültüsünü azaltmak için |
| Hata dalı yok | Tüm kritik düğümlerde error output → Telegram → Stop and Error | Görevin 5. maddesi |
| Sheet güncellemesinden önce 1 dk bekleme, bildirim ve güncelleme paralel | Sıralı akış: geçmiş → bildirim → master güncelleme | Bildirim kaybolursa değişiklik tekrar yakalanabilsin diye |
| Hindistan saati, İngilizce mesajlar | `Europe/Istanbul`, Türkçe bildirim metni; düğüm adları İngilizce | Proje kuralları |

Şablondan korunanlar: Schedule tetikleyicisi, Google Sheets'te master (son fiyat)
ve geçmiş sayfaları, Code düğümünde fiyat normalizasyonu ve Telegram bildirimi.

## Depolama: Google Sheets

Tek bir Google Sheets dosyasında iki sayfa gerekir. Başlık satırları aşağıdaki gibi olmalı:

- `price_history`: `scraped_at | name | price | price_cents | review_count | product_url | change_type | previous_price`
- `latest_prices`: `product_url | name | price | price_cents | review_count | scraped_at`

`price_history` her çalışmada bütün ürünleri ekler; fiyat geçmişi ve tarih damgası
bu sayfada tutulur. `latest_prices` her ürünün son görülen fiyatıdır ve bir sonraki
çalışmada karşılaştırma referansı olarak kullanılır. Siteden kalkan bir ürün
`latest_prices` sayfasında kalır ama bildirim üretmez. Kaldırılan ürünlerin
bildirimi kapsam dışında bırakıldı.

## Import sonrası kurulum

1. n8n'de *Import from File* ile `workflow.json` dosyasını içe aktarın.
2. Üç Google Sheets düğümünde Google Sheets credential'ını seçin ve
   `REPLACE_WITH_SPREADSHEET_ID` değerini kendi dosyanızın ID'siyle değiştirin.
3. İki Telegram düğümünde Telegram Bot credential'ını seçin ve
   `REPLACE_WITH_TELEGRAM_CHAT_ID` değerini kendi sohbet ID'nizle değiştirin.
4. *Manual Test Trigger* ile bir kez çalıştırın. İlk çalışma başlangıç kaydını
   oluşturur, sonra workflow'u aktif hale getirin.

`workflow.json` içinde gerçek credential, sheet ID'si veya chat ID'si yok.

## Doğrulama: ne yapıldı, ne yapılmadı

**n8n'de canlı çalıştırılmadı.** Ekran görüntüsü de yok. Elimde n8n ortamı yoktu
ve brief'e göre zorunlu değil. Bunun yerine `tests/verify_workflow.mjs` scripti
`workflow.json` içindeki Code düğümlerinin JavaScript'ini **birebir** çıkarıp Node.js
ile çalıştırıyor:

```bash
node B-n8n/tests/verify_workflow.mjs            # gerçek siteye karşı dahil
node B-n8n/tests/verify_workflow.mjs --offline  # yalnızca kontrollü senaryolar
```

Kontrol edilenler (18 kontrol, hepsi geçti):

- Graf: düğüm adları benzersiz, bütün bağlantı hedefleri var, gerekli düğüm tipleri mevcut, her kritik düğümün error output'u hata dalına bağlı, master güncellemesi bildirimden sonra, JSON'da credential yok.
- **Gerçek site:** 20 sayfa gezildi ve sitenin bildirdiği sayıyla aynı 117 benzersiz ürün toplandı. Bütün fiyatlar sayı, bütün linkler mutlak.
- Kontrollü senaryolar: 3 sayfalı sahte site, `$1,139.54` ayrıştırma, site kapalı, ara sayfada 404, sayfalama döngüsü, ürünsüz sayfa, bozuk fiyat, eksik tarama, ilk çalışma, değişiklik yok, yeni ürün + düşüş + artış, yerel sayı formatı, çoklu hatanın tek alarma indirgenmesi.

Bu script n8n'in kendi çalışma zamanını taklit etmez. Google Sheets/Telegram
düğüm parametrelerinin ve error output yönlendirmesinin n8n içindeki davranışı
import edilip çalıştırılmadan doğrulanmış sayılmaz. Code düğümündeki
`this.helpers.httpRequest` testte `fetch` ile taklit edildi.
