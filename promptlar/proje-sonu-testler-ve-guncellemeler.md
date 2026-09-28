# Proje Sonu — Testler ve Güncellemeler — Promptlar

Zorunlu bölümler bittikten sonra yazılan testler, ek özellikler ve son kontrollere ait promptlar (`proje-sonu`).
Promptlar silinmeden, sırasıyla ve yazıldığı gibi (yazım hataları dahil) aktarıldı. Sıra numaraları [`A-claude-code.md`](A-claude-code.md) ve [`B-n8n.md`](B-n8n.md) dosyalarından devam eder. Bu dosyadaki promptların hepsi Claude Code'a yazıldı.
Orijinal gönderim saatleri kayıtlı olmadığı için eklenmedi. Kullanıcının sorduğu ve promptlara eklenmemesini istediği iki bilgi sorusu (devir kararının nasıl verildiği) ile bu isteklere bağlı mesajlar bu dosyada yer almıyor.

## 19. `proje-sonu` — Claude Code

~~~text
Tamam o zaman ilk olarak bizim prompts.json'u promptlar diye bir dosyaya ayır ve A B olarak ayır zaten hepsinin aşama label'ı var o labellar kalsın.
Bundan sonraki Yazdıklarımı da proje sonu gibi yeni bir json'a ekleyebiriliz aynı formatta olacak şekilde.
Readme'ye bitiş saatini ve takılınan yerleri ekle ben şimdi burada gemini free tier kotası ve openai key olmama sorunundan bahset, başka aklına bir şey gelirse pop up ile bana sorabilirsin

Onlar dışında
Özet sayfasını html olarak da görüntüleme yapalım
ve dediğin gibi sızıntı kontrolünü tekrarlanabilir hale getirelim
~~~

## 20. `proje-sonu` — Claude Code

~~~text
Özetteki classifylar gemini ile yapılmış halini bırakma son olarak sen kendin classify et, çünkü gemini free tier olduğu için sen daha iyi classfiy edersin normal şartlarda prodda iyi model kullanılır.
Ve claffiy promptunu zero shot yapmayalım, few shot'a çevirelim. ama direkt elimizdeki örneklerden verme her bir kategori için 1 örnek ver ama test etmene gerek yok zaten prompt değişecek sadece.
Bu dediğimi yap sonra başka ne ekleyelim biraz öneriler sun
~~~

## 21. `proje-sonu` — Claude Code

~~~text
Bir de kategorilere istenmeyen mesaj diye bir kategori ekle, bunlar reklam veya benzeri şeyler olacak şekilde. sonra sen tekrar sınıflandır
~~~

## 22. `proje-sonu` — Claude Code

~~~text
Başka ne önerilerin var öncekiler ağırlıklı olarak bende olmayan servisleri kullanmamı gerektiriyor. Ona göre öneride bulun
~~~

## 23. `proje-sonu` — Claude Code

~~~text
Github actions ile birim testlerini otomatize yapmayı ve prompt injection testleri ekleyelim
~~~

## 24. `proje-sonu` — Claude Code

~~~text
Push tamam testler tamam başka ne yapabilir bir kaç farklı öneri daha ver öncekilerde kalan önerilerini beğenmedim veya soruna yol açabilecek şeyler
~~~

## 25. `proje-sonu` — Claude Code

~~~text
Python sürüm uyarısını ekle
Adım 3te bahsettiğim uyarısı ekle
Readme'yi bir topla
bir de son olarak kanal bazlı özet yap whatsapp ve intragram ayrımını ekle
~~~

## 26. `proje-sonu` — Claude Code

~~~text
Bir de committen önce şunu ekle bitirdiğimiz saati zorunlulukların bittiği saat olarka düzelt 13.35'i de testler ve eklemelerin bittiği saat olarak ekle sonra bana revize ettğin commit'i ver
~~~

## 27. `proje-sonu` — Claude Code

~~~text
şimdi son olarka her şeyi bütün bir kontrol et detaya in sonra teslim edeceğim tamam ise
~~~
