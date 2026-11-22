// Widget Scriptable + Phím tắt: giá MacBook thấp nhất theo cấu hình mục tiêu.
// Đọc data/summary.txt do GitHub Actions tạo mỗi sáng (cùng nội dung Phím tắt "Giá Mac").
// Chạy thử trên máy: node iphone/widget.js   (SITE=http://localhost:8765/ node iphone/widget.js để thử bản local)
const SITE = (typeof process !== 'undefined' && process.env.SITE) || 'https://hienphuong99.github.io/MacbookPrice/';
const isScriptable = typeof ListWidget !== 'undefined';
const get = u => isScriptable ? new Request(u).loadString() : fetch(u).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); });

async function load() {
  const txt = await get(SITE + 'data/summary.txt?_=' + Date.now());
  const lines = txt.trim().split('\n');
  if (!/^Giá MacBook/.test(lines[0] || '')) throw new Error('Sai định dạng summary.txt');
  return { text: txt.trim(), head: lines[0], rows: lines.slice(1, -2), deal: lines[lines.length - 2] };
}

function widget(d, err) {
  const w = new ListWidget();
  w.url = SITE + '#deal';
  w.backgroundGradient = Object.assign(new LinearGradient(), {
    locations: [0, 1],
    colors: [Color.dynamic(new Color('#eaf2ff'), new Color('#0b1430')), Color.dynamic(new Color('#f4ecff'), new Color('#1c0f33'))],
  });
  w.setPadding(12, 14, 12, 14);
  const fg = Color.dynamic(Color.black(), Color.white());
  const line = (s, size, bold, op = 1) => { const t = w.addText(s); t.font = bold ? Font.boldSystemFont(size) : Font.systemFont(size); t.textColor = fg; t.textOpacity = op; t.lineLimit = 1; t.minimumScaleFactor = .7; return t; };
  if (err) { line('Giá MacBook', 13, true); line('Lỗi tải: ' + err, 11, false, .7); return w; }
  const big = config.widgetFamily === 'large' ? 9 : config.widgetFamily === 'medium' ? 4 : 3;
  line(d.head.replace('Giá MacBook · ', 'Giá Mac · '), 11, true, .6);
  w.addSpacer(4);
  for (const r of d.rows.slice(0, big)) {
    const [name, rest] = r.replace(/^[✅•]\s*/, '').split(': ');
    line(config.widgetFamily === 'small' ? `${name.replace(/^Air /, 'A')}  ${rest.split(' ')[0]}` : `${name}  ${rest}`, 13, false);
  }
  w.addSpacer();
  line(d.deal, 11, true, .75).textColor = Color.dynamic(new Color('#1f8f3a'), new Color('#4cd964'));
  w.refreshAfterDate = new Date(Date.now() + 3 * 3600e3);
  return w;
}

async function main() {
  let d, err;
  try { d = await load(); } catch (e) { err = e.message || String(e); }
  const msg = d ? d.text : 'Lỗi tải giá MacBook: ' + err;
  if (!isScriptable) { console.log(msg); if (err) process.exitCode = 1; return; }
  Script.setShortcutOutput(msg);            // Phím tắt nhận chữ này
  const w = widget(d, err);
  if (config.runsInWidget) Script.setWidget(w);
  else if (config.runsInApp) await w.presentMedium();
  Script.complete();
}

main();
