// Verifies B-n8n/workflow.json without an n8n installation:
// structural checks on the graph, then the exact Code-node JavaScript is executed
// against the live test site and against controlled change/error scenarios.
// Usage: node B-n8n/tests/verify_workflow.mjs [--offline]
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const workflow = JSON.parse(readFileSync(new URL('../workflow.json', import.meta.url), 'utf8'));
const offline = process.argv.includes('--offline');
const nodes = new Map(workflow.nodes.map((node) => [node.name, node]));
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
let passed = 0;

async function check(name, fn) {
  await fn();
  passed += 1;
  console.log(`ok - ${name}`);
}

// Minimal stand-ins for the n8n Code-node globals used by this workflow.
function runCode(nodeName, { input = [], refs = {}, httpRequest, prevNode = 'Previous Node' } = {}) {
  const code = nodes.get(nodeName).parameters.jsCode;
  const wrap = (items) => ({ all: () => items, first: () => items[0] });
  const $ = (name) => {
    assert.ok(nodes.has(name), `Code references unknown node: ${name}`);
    return wrap(refs[name] ?? []);
  };
  const fn = new AsyncFunction('$input', '$', '$prevNode', '$execution', code);
  const context = { helpers: { httpRequest: httpRequest ?? liveRequest } };
  return fn.call(context, wrap(input), $, { name: prevNode }, { id: 'test' });
}

async function liveRequest({ url, timeout }) {
  const response = await fetch(url, { signal: AbortSignal.timeout(timeout) });
  if (!response.ok) throw new Error(`Request failed with status code ${response.status}`);
  return { statusCode: response.status, body: await response.text() };
}

function page(cards, { next = null, total = null } = {}) {
  const body = cards.map(([id, name, price, reviews]) => `
    <div class="card thumbnail" itemscope itemtype="https://schema.org/Product">
      <span itemprop="price">${price}</span>
      <a href="/test-sites/e-commerce/static/product/${id}" class="title" title="${name}" itemprop="name">${name}</a>
      <p class="review-count"><span itemprop="reviewCount">${reviews}</span> reviews</p>
    </div>`).join('');
  const count = total === null ? '' : `<p class="item-count">${total} items</p>`;
  const nextLink = next ? `<a class="page-link next" href="${next}" rel="next">&rsaquo;</a>` : '';
  return `<html>${count}${body}${nextLink}</html>`;
}

const fakeSite = (pages) => async ({ url }) => {
  const key = new URL(url).search || '?page=1';
  if (!(key in pages)) throw new Error('Request failed with status code 404');
  return { statusCode: 200, body: pages[key] };
};

const products = (items) => items.map((json) => ({ json }));
const product = (id, price) => ({
  scraped_at: '2026-09-28T06:00:00.000Z', name: `Laptop ${id}`, price, price_cents: Math.round(price * 100),
  review_count: 1, product_url: `https://webscraper.io/test-sites/e-commerce/static/product/${id}`,
});
const sheetRow = (id, cents) => ({ json: { product_url: product(id, 0).product_url, price_cents: String(cents) } });

await check('graph: node names unique, every connection target exists', () => {
  assert.equal(nodes.size, workflow.nodes.length);
  for (const [source, { main }] of Object.entries(workflow.connections)) {
    assert.ok(nodes.has(source), source);
    for (const target of main.flat()) assert.ok(nodes.has(target.node), `${source} -> ${target.node}`);
  }
});

await check('graph: required steps are present', () => {
  const types = workflow.nodes.map((node) => node.type);
  for (const type of ['scheduleTrigger', 'googleSheets', 'telegram', 'stopAndError']) {
    assert.ok(types.includes(`n8n-nodes-base.${type}`), type);
  }
  assert.equal(nodes.get('Daily 09:00 Trigger').parameters.rule.interval[0].triggerAtHour, 9);
  assert.equal(workflow.settings.timezone, 'Europe/Istanbul');
});

await check('graph: every failing step routes to the error alert and ends in Stop and Error', () => {
  for (const name of ['Fetch All Pages', 'Parse Products', 'Read Latest Prices', 'Detect Changes',
    'Append Price History', 'Build Change Summary', 'Send Change Alert', 'Update Latest Prices']) {
    assert.equal(nodes.get(name).onError, 'continueErrorOutput', name);
    assert.deepEqual(workflow.connections[name].main[1].map((t) => t.node), ['Build Error Alert'], name);
  }
  assert.equal(workflow.connections['Send Error Alert'].main[0][0].node, 'Mark Execution Failed');
});

await check('graph: master sheet is updated only after the notification step', () => {
  assert.deepEqual(workflow.connections['Has Changes?'].main.map((out) => out[0].node),
    ['Send Change Alert', 'Restore Product Rows']);
  assert.equal(workflow.connections['Send Change Alert'].main[0][0].node, 'Restore Product Rows');
  assert.equal(workflow.connections['Restore Product Rows'].main[0][0].node, 'Update Latest Prices');
});

await check('graph: no credentials or real identifiers are embedded', () => {
  const text = JSON.stringify(workflow);
  assert.ok(!('credentials' in Object.assign({}, ...workflow.nodes)));
  assert.ok(text.includes('REPLACE_WITH_SPREADSHEET_ID') && text.includes('REPLACE_WITH_TELEGRAM_CHAT_ID'));
});

if (!offline) {
  await check('live site: follows every page and parses numeric prices', async () => {
    const pages = await runCode('Fetch All Pages');
    assert.ok(pages.length > 1, 'more than the first page was fetched');
    const parsed = (await runCode('Parse Products', { input: pages })).map((item) => item.json);
    const declared = Number(pages[0].json.html.match(/class="item-count">\s*(\d+)/)[1]);
    assert.equal(parsed.length, declared);
    assert.equal(new Set(parsed.map((p) => p.product_url)).size, parsed.length);
    for (const p of parsed) {
      assert.equal(typeof p.price, 'number');
      assert.ok(p.price > 0 && Number.isInteger(p.price_cents) && Number.isInteger(p.review_count));
      assert.match(p.product_url, /^https:\/\/webscraper\.io\/test-sites\/e-commerce\/static\/product\/\d+$/);
      assert.ok(p.name.length > 0);
    }
    console.log(`   ${pages.length} pages, ${parsed.length} products, e.g. ${JSON.stringify(parsed[0])}`);
  });
}

await check('scrape: follows rel="next" across a controlled 3-page site', async () => {
  const site = fakeSite({
    '?page=1': page([[1, 'A', '$10.00', 1]], { next: '?page=2', total: 3 }),
    '?page=2': page([[2, 'B', '$1,139.54', 0]], { next: '?page=3', total: 3 }),
    '?page=3': page([[3, 'C &amp; D', '$5.5', 7]], { total: 3 }),
  });
  const pages = await runCode('Fetch All Pages', { httpRequest: site });
  const parsed = (await runCode('Parse Products', { input: pages })).map((item) => item.json);
  assert.deepEqual(parsed.map((p) => [p.name, p.price, p.price_cents, p.review_count]),
    [['A', 10, 1000, 1], ['B', 1139.54, 113954, 0], ['C & D', 5.5, 550, 7]]);
});

await check('error: site unreachable fails the scrape step', async () => {
  const down = async () => { throw new Error('getaddrinfo ENOTFOUND'); };
  await assert.rejects(runCode('Fetch All Pages', { httpRequest: down }), /Sayfa açılamadı/);
});

await check('error: failure on a middle page fails the whole run', async () => {
  const site = fakeSite({ '?page=1': page([[1, 'A', '$1.00', 1]], { next: '?page=2' }) });
  await assert.rejects(runCode('Fetch All Pages', { httpRequest: site }), /404/);
});

await check('error: pagination loop is detected', async () => {
  const site = fakeSite({ '?page=1': page([[1, 'A', '$1.00', 1]], { next: '?page=1' }) });
  await assert.rejects(runCode('Fetch All Pages', { httpRequest: site }), /döngüsü/);
});

await check('error: page without products fails instead of storing an empty run', async () => {
  await assert.rejects(runCode('Parse Products', { input: [{ json: { page_url: 'https://x/', html: '<html></html>' } }] }),
    /ürün bulunamadı/);
});

await check('error: malformed price or missing field fails the run', async () => {
  const bad = { json: { page_url: 'https://x/', html: page([[1, 'A', 'call us', 1]]) } };
  await assert.rejects(runCode('Parse Products', { input: [bad] }), /Eksik veya beklenmeyen/);
});

await check('error: collected count differs from the site total', async () => {
  const short = { json: { page_url: 'https://x/', html: page([[1, 'A', '$1.00', 1]], { total: 117 }) } };
  await assert.rejects(runCode('Parse Products', { input: [short] }), /117 ürün bildiriyor, 1/);
});

const current = products([product(1, 100), product(2, 250.5), product(3, 80)]);

await check('change: first run with an empty sheet sends one baseline summary', async () => {
  const detected = await runCode('Detect Changes', { input: [{ json: {} }], refs: { 'Parse Products': current } });
  assert.ok(detected.every((item) => item.json.change_type === 'baseline'));
  const [summary] = await runCode('Build Change Summary', { refs: { 'Detect Changes': detected } });
  assert.equal(summary.json.notify, true);
  assert.match(summary.json.message, /3 ürün başlangıç kaydı/);
});

await check('change: identical prices produce no notification', async () => {
  const sheet = [sheetRow(1, 10000), sheetRow(2, 25050), sheetRow(3, 8000)];
  const detected = await runCode('Detect Changes', { input: sheet, refs: { 'Parse Products': current } });
  assert.ok(detected.every((item) => item.json.change_type === 'unchanged'));
  const [summary] = await runCode('Build Change Summary', { refs: { 'Detect Changes': detected } });
  assert.equal(summary.json.notify, false);
});

await check('change: new product, price drop and price rise are reported together', async () => {
  const sheet = [sheetRow(1, 12000), sheetRow(2, 20000)];
  const detected = await runCode('Detect Changes', { input: sheet, refs: { 'Parse Products': current } });
  assert.deepEqual(detected.map((item) => item.json.change_type), ['price_down', 'price_up', 'new']);
  assert.equal(detected[0].json.previous_price, 120);
  const [summary] = await runCode('Build Change Summary', { refs: { 'Detect Changes': detected } });
  assert.equal(summary.json.notify, true);
  assert.match(summary.json.message, /Yeni: 1 \| Düşen: 1 \| Artan: 1/);
  assert.match(summary.json.message, /\$120\.00 → \$100\.00/);
});

await check('change: locale-formatted sheet values do not create false changes', async () => {
  const sheet = [{ json: { product_url: product(2, 0).product_url, price_cents: '25.050' } }];
  const detected = await runCode('Detect Changes', { input: sheet, refs: { 'Parse Products': products([product(2, 250.5)]) } });
  assert.equal(detected[0].json.change_type, 'unchanged');
});

await check('error branch: many failed items collapse into one alert', async () => {
  const failed = [{ json: { error: 'Site down' } }, { json: { error: 'Site down' } }];
  const alerts = await runCode('Build Error Alert', { input: failed, prevNode: 'Fetch All Pages' });
  assert.equal(alerts.length, 1);
  assert.match(alerts[0].json.message, /BAŞARISIZ[\s\S]*Adım: Fetch All Pages[\s\S]*Hata: Site down/);
});

console.log(`\n${passed} checks passed${offline ? ' (offline: live site check skipped)' : ''}.`);
