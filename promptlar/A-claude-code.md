# Bölüm A — Promptlar

Genel planlama (`planning`), Bölüm A (`A`) ve Codex'ten Claude Code'a geçiş (`handover-claude-code`) promptları.
Promptlar silinmeden, sırasıyla ve yazıldığı gibi (yazım hataları dahil) aktarıldı. Sıra numaraları iki dosyada ortak, yani atlanan numaralar diğer dosyadadır. 1-13 arası Codex'e, 14 ve sonrası Claude Code'a yazıldı. 19 ve sonrası [`proje-sonu.json`](proje-sonu.json) dosyasında.
Orijinal gönderim saatleri kayıtlı olmadığı için eklenmedi. 15. kayıt serbest metin değil, Claude Code'un çoktan seçmeli sorusuna verilen cevaplardır.

## 1. `planning` — Codex

~~~text
case-brief.md'yi ve mesajlar.jon'u incele ve hangi modelle en uygun biçimde yapılacağına karar ver 
~~~

## 2. `planning` — Codex

~~~text
6 sol yok ki 6 astra var codex'te sadece
~~~

## 3. `planning` — Codex

~~~text
bu case'i oku iyice incele kararları ver soracağın soru olursa onları da sor önce bir implementasyon planı çıkart ben onaylarsam önce bölüm A sonra bölüm B'yi yapalım şimdi ilk olarak case-brief.md ve mesajlar.json'u incele
~~~

## 4. `A` — Codex

~~~text
Mesajları sen classify etmişsin fakat prod'a çıkacağa göre yapmamız lazım o yüzden sen bunu openai api chat completions ve gemini ile entegre et belki en son zaman kalsırsa local llm ile yapmak adına bi şey ekleriz ama şimdilik onu ekleme, ancak bende hali hazırda api key olmadığı için sen classify et ama  normal şartlarda api key ile yapacağız .env dosyası açıp ona da api keyleri girecek yer bırak ben uğraşıren api key ayarlamaya çalışacağım.



Bir yandan senden istediğim prompts diye bir json çıkart, içine yazdıklarımı tek tek json veya jsonl olarak sıra sıra not al



istenmeyen etki başlığını hassas\_konu olarka değiştir ve konular arasına "-" değil "\_" yani alt tire koy.

Kodu türkçe yapma sadece konu başlıkları ve kullanıcıya gidecek olan kısımlar türkçe olacak



Sorularının cevapları:

1. saat 11'de aldım teslim süresi 14'te yani 13.45 gibi kontroller ile bitmiş olması lazım
2. Bu ilk sohbet kayıtları direkt olarak bu konuşmanın başından başlat.



Bölüm A'dan başla ben de bir yandan github reposu ayarlayacağım sen hiçbir şey push etmiyosun push atılması gerektiği yerlerde yazmayı planladığın commit mesajını bana iletiyosun ben kontrol edip ona göre ayarlayacağım.

Git ignore dosyası oluştur .env ve gerekli başka bir şey olursa onları da ekle
~~~

## 5. `A` — Codex

~~~text
Sadece bu directory'e yaz kodları bu arada ve orijinal şu anda buradaki 2 dosyayı elleme onlar orijinal hali ile kalacak
~~~

## 6. `A` — Codex

~~~text
Ben github repo'sunu oluşturdum ve bağladım. Dediğim gibi commit zamanlarında bana tavsiye ettiğin mesajı ver sen commit atma ben kontrol edeceğim.
~~~

## 7. `A` — Codex

~~~text
Gemini api key'i oluşturup ekledim onun testlerini de A aşamasının en sonunda yapacağız. Ve ilk commiti de gerçekleştirdim.
~~~

## 8. `A` — Codex

~~~text
Az önce bağlantı koptu kaldığın yerden devam et ve buna ek olarak Gemini veya openai'a classify için verdiğin promptu dosya içine değil harici bir variable olarak bağlayalım. enviroment içine dosya yolu olarak koy ve "classift\\\_prompt.txt" olarak text dosyasından alsın ve bunu prompts diye ayrı bir dosyanın içine koy ileride başka şeyler eklenecek olursa tüm promptlar bir arada dursun.
~~~

## 9. `A` — Codex

~~~text
Bir de öncelikli olarak: bana bir dosya çıkart, içine yapılanlar ve yapılması planlananları detaylı bir şekilde yaz ve bunu gitignore'a da ekle pushlamayalım benim için o dosya
~~~

## 10. `A` — Codex

~~~text
Bölüm A durum raporu ver şimdi kısa ve öz olarak
~~~

## 11. `A` — Codex

~~~text
Bir de Commit önerisi ver 
~~~

## 14. `handover-claude-code` — Claude Code

~~~text
Şimdi ilk olarak bu directory'deki tüm dosyaları incele. Bize ilk verilen orijinal dosyalar case-brief.md ve mesajlar.json dosyaları. Bu directory'de gördüğün her şeyi codex ile yaptım ama usage limitim bitti senin ile devam edeceğiz.
İlk olarak hiçbir commit atma commit atılacağı zaman bana sadece mesajı öneri ver ben inceleyip atacağım.
Sana yazdığım her mesajı prompts.json dosyasına aynı formatta ekleyeceksin.

Şimdi önce case-brief'i sonra kodları sonra da prompts.json'u ve LOCAL_PROGRESS.md'yi incele benim codex'e verdiğim en son prompttan devam et.
~~~

## 16. `A` — Claude Code

~~~text
Öncelikle şunu değiştirelim prompts dosyasının adını değiştirelim veya classify.txt dosyasını ayrıca bir yerde tutalım çünkü case'in istediği promptlar dosyasında bizim verdiğimiz promptlar olacak. Bu case özelinde classif_prompt'u uygun gördüğün bir yere koy ve .env içinde değiştir. şimdilik sadece prompts.json üzerinden ilerleyelim en son A B aşamaları için ayırırız onu kafana takma.

Son verdiğim promtu da eklememişsin onu da ekle bu yazdığımla birlikte, yani bundan sonra sana prompt verdiğimde ilk işin onu prompts.json'a eklemek olacak.

Şimdi öncelikli olarak kapsamlı test yap bir kaç tane çok uzun tutma sonra ürün arama bonusuna geçelim.

Ben bir push daha attım sen yine commit önerisinde bulun uygun zamanlarda.
~~~

## 17. `A` — Claude Code

~~~text
Bir de .env'i kayıt etmediğim için gemini key yenilenmemiş şimdi kayıt ettim tekrardan denyebilirsin
~~~

## 18. `A` — Claude Code

~~~text
1. Gemini isteğini küçük eski bir model ile dene olmuyorsa sadece alt yapı kodunu tekrar gözden geçirmen yeterli gerçek key ile denenir.
2. Her şey bitti ise total bir detaylı test gerçekleştir.
3. Bunlardan sonra ne ekleyebiliriz daha iyi bir projeye çevirmek için neler yapabiliriz onlara bakacağız
~~~
