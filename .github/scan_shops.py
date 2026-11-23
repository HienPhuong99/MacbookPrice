"""Tự quét giá MacBook trên các shop có API JSON công khai -> data/shops.json (cùng schema listing với macbook.json).

Bù cho bot ghi sheet khi nó ngừng chạy. Không API key, chỉ thư viện chuẩn. scan.py gộp file này vào macbook.json.
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import scan  # noqa: E402  (dùng chung parse_targets / fetch_sheet_csv)

OUT_PATH = os.path.join('data', 'shops.json')
UA = {'User-Agent': 'Mozilla/5.0 (MacbookPriceBot)'}
# ponytail: chỉ shop có JSON sẵn. Woo "biến thể" của 2T Mobile bị bỏ qua: thuộc tính chỉ ghi "Cấu hình 1..N"
# (không có RAM/SSD, kiểm 23/11) và toàn máy M5/M6 ngoài danh sách mục tiêu — cần thì đọc mô tả từng biến thể.
PHONE_RE = re.compile(r'(?:\+?84|0)[\d .]{8,12}\d')  # tiêu đề tin chợ đôi khi ghi SĐT -> che
MIN_PRICE = 10_000_000  # dưới mức này là phụ kiện / đặt cọc / máy đời cũ
FLAG_RE = re.compile(r'\bmdm\b|bypass|icloud|lỗi màn|đốm|sọc màn|ố màn|bể màn|vỡ màn|hư main', re.IGNORECASE)
SHOPS = [
    {'name': 'MacShop24h', 'kind': 'sapo', 'base': 'https://macshop24h.vn'},
    {'name': 'Lâm Phong Store', 'kind': 'sapo', 'base': 'https://lamphongstore.com'},
    {'name': 'MacVN', 'kind': 'woo', 'base': 'https://macvn.com.vn'},
    {'name': '2T Mobile', 'kind': 'woo', 'base': 'https://2tmobile.com'},
    {'name': 'Chợ Tốt', 'kind': 'chotot', 'base': 'https://gateway.chotot.com/v1/public/ad-listing'},
]

CHIP_RE = re.compile(r'\bM([1-9])(?:\s*(Pro|Max|Ultra))?\b', re.IGNORECASE)
RAM_RE = re.compile(r'\b(8|16|18|24|32|36|48|64|96|128)\s*GB(?!\s*SSD)', re.IGNORECASE)
SSD_RE = re.compile(r'\b(256|512)\s*GB\b|\b([1248])\s*TB\b', re.IGNORECASE)
SCREEN_RE = re.compile(r"""\b(13|14|15|16)(?:[.,]\d)?\s*(?:inch|in\b|"|”|''|'|’’|’|-inch)""", re.IGNORECASE)
CPUGPU_RE = re.compile(r'(\d+)\s*CPU\s*/\s*(\d+)\s*GPU', re.IGNORECASE)
NEW_RE = re.compile(r'new\s*seal|newseal|mới\s*100|chính hãng|\bnew\b|\bmới\b', re.IGNORECASE)
USED_RE = re.compile(r'like\s*new|\bcũ\b|đã qua sử dụng|99\s*%|98\s*%|trôi bảo hành|open\s*box|\bused\b', re.IGNORECASE)


def strip_html(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def parse_title(title, extra=''):
    """Đọc chip / RAM / SSD / màn / tình trạng từ tên sản phẩm (+ mô tả ngắn). Thiếu chip/RAM/SSD -> None."""
    t = f'{title} {extra}'
    m = CHIP_RE.search(title) or CHIP_RE.search(t)
    if not m or not re.search(r'mac\s*book', t, re.IGNORECASE):
        return None
    chip = f'M{m[1]}' + (f' {m[2].capitalize()}' if m[2] else '')
    if not m[2] and re.search(r'\bair\b', t, re.IGNORECASE):
        chip = 'Air ' + chip
    ssd_m = SSD_RE.search(title) or SSD_RE.search(t)
    ram_candidates = [int(x) for x in RAM_RE.findall(title) or RAM_RE.findall(t)]
    if not ssd_m or not ram_candidates:
        return None
    ssd = int(ssd_m[1]) if ssd_m[1] else int(ssd_m[2]) * 1024
    ram = next((r for r in ram_candidates if r != ssd), None)
    if ram is None or ram >= 256:
        return None
    scr = SCREEN_RE.search(title) or SCREEN_RE.search(t)
    cg = CPUGPU_RE.search(t)
    used = USED_RE.search(t)
    cond = 'Cũ' if used else 'Mới' if NEW_RE.search(t) else ''
    return {'chip': chip, 'ram': ram, 'ssd': ssd, 'screen': int(scr[1]) if scr else None,
            'cpugpu': f'{cg[1]}CPU/{cg[2]}GPU' if cg else '', 'cond': cond}


def match_target(p, targets):
    for t in targets:
        same_chip = t['chip'] == p['chip'] or (t['chip'] == f"M{p['chip'][-1]}" and p['chip'] == f"Air M{p['chip'][-1]}")
        if not same_chip or t['ram'] != p['ram'] or t['ssd'] != p['ssd']:
            continue
        if p['screen'] and t.get('screens') and p['screen'] not in t['screens']:
            continue
        need = (t.get('need') or '').lower()
        if p['cond'] and need in ('mới', 'cũ') and p['cond'].lower() != need:
            continue
        return t
    return None


def fetch_json(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        text = r.read().decode('utf-8', 'replace')
    i = min(x for x in (text.find('['), text.find('{')) if x >= 0)  # 2T Mobile chèn HTML rác trước JSON
    return json.loads(text[i:])


NEG_RE = re.compile(r'không|\bko\b|\bk\b|chưa|sạch|\bno\b|free|thoát|zin', re.IGNORECASE)


def flag_of(text):
    """Cờ đầu tiên không bị phủ định ("không MDM", "icloud sạch", "full sạch" -> bỏ qua)."""
    m = next((m for m in FLAG_RE.finditer(text) if not NEG_RE.search(text[max(0, m.start() - 25):m.end() + 8])), None)
    if not m:
        return ''
    w = m[0].lower()
    return 'mdm' if w in ('mdm', 'bypass') else 'icloud' if w == 'icloud' else 'lỗi'


def sapo_products(shop, targets=None):
    out = []
    for page in range(1, 9):
        items = fetch_json(f"{shop['base']}/products.json?limit=250&page={page}").get('products') or []
        for p in items:
            vs = [v for v in p.get('variants') or [] if v.get('available') and v.get('price')]
            if not vs:
                continue
            v = min(vs, key=lambda x: x['price'])  # các màu cùng cấu hình -> 1 tin, giá thấp nhất
            out.append({'id': str(p['id']), 'title': p.get('name', ''), 'extra': strip_html(p.get('summary', ''))[:300],
                        'price': int(v['price']), 'list': int(v.get('compare_at_price') or 0) or None,
                        'url': shop['base'] + (p.get('url') or v.get('url') or '')})
        if len(items) < 250:
            break
    return out


def woo_products(shop, targets=None):
    out = []
    for page in range(1, 9):
        items = fetch_json(f"{shop['base']}/wp-json/wc/store/v1/products?search=macbook&per_page=100&page={page}")
        for p in items:
            pr = p.get('prices') or {}
            unit = 10 ** int(pr.get('currency_minor_unit') or 0)
            price = int(pr.get('price') or 0) // unit
            if not price or not p.get('is_in_stock'):
                continue
            reg = int(pr.get('regular_price') or 0) // unit
            out.append({'id': str(p['id']), 'title': html.unescape(p.get('name', '')), 'extra': strip_html(p.get('short_description', ''))[:300],
                        'price': price, 'list': reg if reg > price else None, 'url': p.get('permalink', '')})
        if len(items) < 100:
            break
    return out


def chotot_products(shop, targets):
    """Chợ Tốt (API công khai, mục Laptop cg=5030): 1 truy vấn / (chip, RAM) mục tiêu, tối đa 100 tin mới nhất."""
    out, seen = [], set()
    for q in sorted({f"macbook {t['chip']} {t['ram']}gb".lower() for t in targets}):
        for o in (0, 50):
            ads = fetch_json(f"{shop['base']}?cg=5030&limit=50&o={o}&q={urllib.parse.quote(q)}").get('ads') or []
            for a in ads:
                if a.get('type') != 's' or a['list_id'] in seen or not a.get('price'):
                    continue
                seen.add(a['list_id'])
                out.append({'id': str(a['list_id']), 'title': a.get('subject', ''), 'extra': (a.get('body') or '')[:300],
                            'price': int(a['price']), 'list': None, 'url': f"https://www.chotot.com/{a['list_id']}.htm",
                            'used': True})  # chợ đồ cũ: mặc định là máy cũ
            if len(ads) < 50:
                break
    return out


def scan_shops(targets, today_iso, prev=None, fetchers=None):
    prev_listings = (prev or {}).get('listings', [])
    prev_first = {l['id']: l.get('first') for l in prev_listings}
    fetchers = fetchers or {'sapo': sapo_products, 'woo': woo_products, 'chotot': chotot_products}
    listings, report, status = [], {}, []
    for shop in SHOPS:
        try:
            raw = fetchers[shop['kind']](shop, targets)
        except Exception as e:  # 1 shop lỗi: giữ tin lần trước (giữ nguyên `last`) để giá không nhảy giả
            kept = [l for l in prev_listings if l.get('source') == shop['name']]
            listings += kept
            report[shop['name']] = f'LỖI {type(e).__name__}: {e}'[:160]
            status.append({'shop': shop['name'], 'ok': False, 'n': len(kept), 'note': f"{report[shop['name']][:80]} — giữ {len(kept)} tin lần trước"})
            continue
        n = 0
        for r in raw:
            if r['price'] < MIN_PRICE:
                continue
            p = parse_title(r['title'], r['extra'])
            if p and r.get('used') and p['cond'] != 'Mới':
                p['cond'] = 'Cũ'
            t = p and match_target(p, targets)
            if not t:
                continue
            lid = f"SHOP-{shop['name']}-{r['id']}"
            listings.append({'id': lid, 'first': prev_first.get(lid) or today_iso, 'last': today_iso, 'latest': True,
                             'srcType': 'Chợ tự quét' if r.get('used') else 'Shop tự quét', 'source': shop['name'], 'code': t['code'], 'chip': t['chip'],
                             'cpugpu': p['cpugpu'], 'ram': p['ram'], 'ssd': p['ssd'], 'screen': p['screen'],
                             'cond': p['cond'] or t.get('need') or '', 'battery': None, 'cycle': None, 'warranty': None,
                             'list': r['list'], 'price': r['price'], 'promo': '', 'seller': '' if r.get('used') else shop['name'],
                             'url': r['url'], 'flag': flag_of(f"{r['title']} {r['extra']}"), 'note': PHONE_RE.sub('…', r['title'])[:120]})
            n += 1
        report[shop['name']] = f'{len(raw)} sản phẩm, {n} khớp cấu hình'
        status.append({'shop': shop['name'], 'ok': True, 'n': n, 'note': report[shop['name']]})
    return {'time': today_iso, 'report': report, 'status': status, 'listings': listings}


def main():
    now = datetime.datetime.now(scan.VN_TZ)
    targets = scan.parse_targets(scan.fetch_sheet_csv(scan.SHEET_ID, scan.TAB_TARGETS))
    prev = None
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding='utf-8') as f:
                prev = json.load(f)
        except (OSError, ValueError):
            prev = None
    data = scan_shops(targets, now.date().isoformat(), prev)
    data['time'] = now.isoformat(timespec='seconds')
    os.makedirs('data', exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    for k, v in data['report'].items():
        print(f'{k}: {v}'.encode('ascii', 'replace').decode())
    print(f"{OUT_PATH}: {len(data['listings'])} listings")


if __name__ == '__main__':
    main()
