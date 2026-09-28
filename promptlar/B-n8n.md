# Bölüm B — Promptlar

Bölüm B (`B-planning`) promptları.
Promptlar silinmeden, sırasıyla ve yazıldığı gibi (yazım hataları dahil) aktarıldı. Sıra numaraları iki dosyada ortak, yani atlanan numaralar diğer dosyadadır. 1-13 arası Codex'e, 14 ve sonrası Claude Code'a yazıldı. 19 ve sonrası [`proje-sonu.json`](proje-sonu.json) dosyasında.
Orijinal gönderim saatleri kayıtlı olmadığı için eklenmedi. 15. kayıt serbest metin değil, Claude Code'un çoktan seçmeli sorusuna verilen cevaplardır.

## 12. `B-planning` — Codex

~~~text
Tamam şimdi aşama A'da yaptığımız gibi B'nin üstünden geçelim. Bu konuşmada yeni fikir plan veya hazırda olan planda bir değişiklik olursa LOCAL\_PROGRESS.md'ye ekle
~~~

## 13. `B-planning` — Codex

~~~text
Planın güzel, başlangıç için şu linkteki n8n workflow'unu kullanalım: https://n8n.io/workflows/4640-competitor-price-monitoring-with-web-scrapinggoogle-sheets-and-telegram/ . Gemini API key'ini yeniledim, testlerini yapabilirsin ancak free tier olduğu için request sayısını ve sıklığını minimumda tut, yine tıkanmasın. Buna ek olarak Gemini veya OpenAI'a classify için verdiğin promptu dosya içine gömmek yerine harici bir variable olarak bağlayalım; environment içine dosya yolu olarak koy, "classify_prompt.txt" isimli text dosyasından okusun ve bu dosyayı da "prompts" adında ayrı bir klasörün içine koy ki ileride başka şeyler eklendiğinde tüm promptlar bir arada dursun.
~~~

## 15. `B-planning` — Claude Code

~~~text
[Claude Code çoktan seçmeli soru yanıtları] Bildirim kanalı: Telegram (Recommended). Depolama: Google Sheets (Recommended). n8n ortamı: Yok, sadece JSON üret.
~~~
