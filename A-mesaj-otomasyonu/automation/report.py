"""Single-file HTML summary for the representative; every value is escaped."""
from collections import Counter
from html import escape

from .domain import Topic


STYLE = """
:root { --bg: #f6f7f9; --card: #fff; --text: #1d2330; --muted: #5d6677; --line: #e2e5ea;
        --warn: #b4232a; --warn-bg: #fdecec; --ok: #1f7a3d; --ok-bg: #e7f5ec; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #14171c; --card: #1d2129; --text: #e6e8ec; --muted: #9aa3b2; --line: #2e3440;
          --warn: #ff8a8f; --warn-bg: #3a1f22; --ok: #7fd49a; --ok-bg: #1d3325; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px; background: var(--bg); color: var(--text);
       font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 1.5rem; margin: 0 0 4px; }
.meta { color: var(--muted); margin: 0 0 20px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.stat b { display: block; font-size: 1.6rem; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: .85rem; }
.stat.warn b { color: var(--warn); }
.table-wrap { overflow-x: auto; background: var(--card); border: 1px solid var(--line); border-radius: 10px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; vertical-align: top; padding: 10px 12px; border-bottom: 1px solid var(--line); }
th { font-size: .8rem; text-transform: uppercase; letter-spacing: .03em; color: var(--muted); }
tr:last-child td { border-bottom: 0; }
td.note { color: var(--muted); font-size: .85rem; min-width: 220px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: .8rem; white-space: nowrap; }
.yes { background: var(--warn-bg); color: var(--warn); }
.no { background: var(--ok-bg); color: var(--ok); }
code { font-size: .85rem; }
"""


def render_html(tickets: list[dict], provider: str, model: str | None, errors: list[dict], generated_at: str) -> str:
    counts = Counter(ticket["konu"] for ticket in tickets)
    handoffs = sum(ticket["devret"] for ticket in tickets)
    stats = [(len(tickets), "Toplam mesaj", False), (handoffs, "Temsilciye devredilecek", handoffs > 0),
             (len(errors), "Teknik hata", bool(errors))]
    stats += [(counts[topic.value], topic.value, False) for topic in Topic]
    cards = "".join(
        f'<div class="stat{" warn" if warn else ""}"><b>{value}</b><span>{escape(label)}</span></div>'
        for value, label, warn in stats)
    rows = "".join(
        "<tr>"
        f"<td>{ticket['id']}</td><td><code>{escape(ticket['konu'])}</code></td>"
        f'<td><span class="badge {"yes" if ticket["devret"] else "no"}">{"Evet" if ticket["devret"] else "Hayır"}</span></td>'
        f"<td>{escape(ticket['cevap_taslagi']) or '<em>Yanıt yok</em>'}</td>"
        f'<td class="note">{escape(ticket["not"])}</td>'
        "</tr>" for ticket in tickets)
    source = f"{escape(provider)}" + (f" / {escape(model)}" if model else "")
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Müşteri Talepleri Özeti</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>Müşteri Talepleri Özeti</h1>
<p class="meta">Sınıflandırma: {source} · Oluşturulma: {escape(generated_at)}</p>
<section class="stats">{cards}</section>
<div class="table-wrap">
<table>
<thead><tr><th>ID</th><th>Konu</th><th>Devret</th><th>Cevap taslağı</th><th>Not</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
</main>
</body>
</html>
"""
