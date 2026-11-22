"""Quét Google Sheet 'Dò giá MacBook 2027' -> data/macbook.json (không cần API key)."""
import csv as csv_mod
import datetime
import io
import json
import os
import re
import urllib.parse
import urllib.request

SHEET_ID = '1A_vyHncnOD0s9aiWlJ1qBzIOuGW-ERapP0IAlg9c5-Y'
TAB_LOG = 'Nhật ký'
TAB_TARGETS = 'Cấu hình mục tiêu'
TAB_SETTINGS = 'Cài đặt'

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))
MAX_HISTORY_POINTS = 365
DEFAULT_WINDOW_DAYS = 14
DEFAULT_DEAL_CAP = 32_000_000
DEFAULT_DEAL_DROP_PCT = 0.03
DEFAULT_MAX_LOG_PRICE = 55_000_000
OUT_PATH = os.path.join('data', 'macbook.json')

NUM_RE = re.compile(
    r'^[-+]?\s*[$€₫]?\s*\d[\d.,\s]*\s*(?:đ|₫|vnđ|vnd|\$|€|%)?$',
    re.IGNORECASE,
)

# Các cột riêng tư tuyệt đối không đọc / không xuất ra JSON công khai
PRIVATE_COLUMNS = {
    'link profile người bán',
    'link ảnh (drive)',
}


def parse_num(value):
    s = str(value or '').strip()
    if not s or not NUM_RE.match(s):
        return None
    t = re.sub(r'[^\d.,-]', '', s)
    if re.match(r'^-?\d{1,3}([.,])\d{3}(\1\d{3})*$', t):
        t = re.sub(r'[.,]', '', t)
    elif '.' in t and ',' in t:
        t = t.replace('.', '').replace(',', '.') if t.rfind(',') > t.rfind('.') else t.replace(',', '')
    else:
        t = t.replace(',', '.')
    try:
        n = float(t)
        return int(n) if n.is_integer() else n
    except ValueError:
        return None


def parse_int(value):
    n = parse_num(value)
    if n is None:
        return None
    if isinstance(n, int):
        return n
    return int(n) if float(n).is_integer() else None


def parse_date_iso(value):
    s = str(value or '').strip()
    if not s:
        return None
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})(?:\b|T|\s|$)', s)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        try:
            return datetime.date(y, mo, d).isoformat()
        except ValueError:
            return None
    m = re.match(r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\b|\s|$)', s)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        try:
            return datetime.date(y, mo, d).isoformat()
        except ValueError:
            return None
    return None


def parse_bool(value, default=False):
    s = str(value or '').strip().lower()
    if not s:
        return default
    if s in ('có', 'co', 'true', '1', 'yes', 'y'):
        return True
    if s in ('không', 'khong', 'false', '0', 'no', 'n'):
        return False
    return default


def parse_screens(value):
    seen = set()
    out = []
    for tok in re.findall(r'\d+', str(value or '')):
        n = int(tok)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _read_csv_rows(csv_text):
    clean = (csv_text or '').lstrip('\ufeff')
    return [r for r in csv_mod.reader(io.StringIO(clean)) if any(c.strip() for c in r)]


def _header_map(headers):
    return {h.strip().lower(): i for i, h in enumerate(headers) if h.strip()}


def _cell(row, hmap, *names):
    for name in names:
        idx = hmap.get(name.lower())
        if idx is not None and idx < len(row):
            return row[idx].strip()
    return ''


def parse_settings(csv_text):
    settings = {
        'windowDays': DEFAULT_WINDOW_DAYS,
        'dealCap': DEFAULT_DEAL_CAP,
        'dealDropPct': DEFAULT_DEAL_DROP_PCT,
        'maxLogPrice': DEFAULT_MAX_LOG_PRICE,
        'includeFacebook': False,
    }
    rows = _read_csv_rows(csv_text)
    if len(rows) < 2:
        return settings
    hmap = _header_map(rows[0])
    for r in rows[1:]:
        param = (_cell(r, hmap, 'tham số') or (r[0].strip() if len(r) > 0 else '')).lower()
        val = _cell(r, hmap, 'giá trị') or (r[1].strip() if len(r) > 1 else '')
        if not param:
            continue
        if 'cửa sổ thống kê' in param:
            n = parse_int(val)
            if n is not None and n > 0:
                settings['windowDays'] = n
        elif 'ngưỡng giá deal' in param:
            n = parse_int(val)
            if n is not None and n > 0:
                settings['dealCap'] = n
        elif '% thấp hơn' in param:
            n = parse_num(val)
            if n is not None and n >= 0:
                settings['dealDropPct'] = float(n)
        elif 'giá tối đa' in param:
            n = parse_int(val)
            if n is not None and n > 0:
                settings['maxLogPrice'] = n
        elif 'facebook' in param and 'thống kê' in param:
            settings['includeFacebook'] = parse_bool(val, default=False)
    return settings


def parse_targets(csv_text):
    rows = _read_csv_rows(csv_text)
    if len(rows) < 2:
        return []
    hmap = _header_map(rows[0])
    targets = []
    for r in rows[1:]:
        code = _cell(r, hmap, 'mã cấu hình')
        if not code or code.upper() == 'VÍ DỤ':
            continue
        enabled = parse_bool(_cell(r, hmap, 'bật'), default=True)
        if not enabled:
            continue
        targets.append({
            'code': code,
            'chip': _cell(r, hmap, 'dòng chip'),
            'need': _cell(r, hmap, 'tình trạng cần'),
            'ram': parse_int(_cell(r, hmap, 'ram (gb)')),
            'ssd': parse_int(_cell(r, hmap, 'ssd (gb)')),
            'screens': parse_screens(_cell(r, hmap, 'màn hình chấp nhận')),
            'cap': parse_int(_cell(r, hmap, 'giá trần (đ)')),
            'order': parse_int(_cell(r, hmap, 'thứ tự dòng')),
        })
    return targets


MARKETPLACE_RE = re.compile(r'chợ tốt|chotot|facebook|\bfb\b|marketplace', re.IGNORECASE)


def is_facebook(item):
    return 'facebook' in f"{item.get('srcType', '')} {item.get('source', '')}".lower()


def is_marketplace(item):
    return bool(MARKETPLACE_RE.search(f"{item.get('srcType', '')} {item.get('source', '')}"))


def parse_listings(csv_text):
    rows = _read_csv_rows(csv_text)
    if len(rows) < 2:
        return []
    hmap = {
        k: v for k, v in _header_map(rows[0]).items()
        if k not in PRIVATE_COLUMNS
    }
    by_id = {}
    for r in rows[1:]:
        item_id = _cell(r, hmap, 'id tin')
        code = _cell(r, hmap, 'mã cấu hình')
        if not item_id or item_id.upper().startswith('VD-') or code.upper() == 'VÍ DỤ':
            continue
        list_price = parse_int(_cell(r, hmap, 'giá niêm yết (đ)'))
        sale_price = parse_int(_cell(r, hmap, 'giá sau km (đ)'))
        price = sale_price if sale_price is not None else list_price
        item = {
            'id': item_id,
            'first': parse_date_iso(_cell(r, hmap, 'ngày ghi')),
            'last': parse_date_iso(_cell(r, hmap, 'lần thấy cuối')),
            'latest': parse_bool(_cell(r, hmap, 'mới nhất'), default=False),
            'srcType': _cell(r, hmap, 'loại nguồn'),
            'source': _cell(r, hmap, 'nguồn'),
            'code': code,
            'chip': _cell(r, hmap, 'dòng chip'),
            'cpugpu': _cell(r, hmap, 'cpu/gpu'),
            'ram': parse_int(_cell(r, hmap, 'ram (gb)')),
            'ssd': parse_int(_cell(r, hmap, 'ssd (gb)')),
            'screen': parse_int(_cell(r, hmap, 'màn (inch)')),
            'cond': _cell(r, hmap, 'tình trạng'),
            'battery': parse_int(_cell(r, hmap, 'pin (%)')),
            'cycle': parse_int(_cell(r, hmap, 'cycle')),
            'warranty': parse_int(_cell(r, hmap, 'bảo hành (tháng)')),
            'list': list_price,
            'price': price,
            'promo': _cell(r, hmap, 'khuyến mãi'),
            'seller': _cell(r, hmap, 'người bán'),
            'url': _cell(r, hmap, 'url'),
            'flag': _cell(r, hmap, 'cờ'),
            'note': _cell(r, hmap, 'ghi chú'),
        }
        # Chợ / Facebook là người bán cá nhân -> không công khai tên
        if is_marketplace(item):
            item['seller'] = ''
        # ID trùng -> giữ dòng cuối
        if item_id in by_id:
            del by_id[item_id]
        by_id[item_id] = item
    return list(by_id.values())


def update_history(prev_history, listings, scan_date_iso, window_days=DEFAULT_WINDOW_DAYS, include_facebook=False):
    history = {
        k: [list(pt) for pt in pts]
        for k, pts in (prev_history or {}).items()
        if isinstance(pts, list)
    }
    scan_date = datetime.date.fromisoformat(scan_date_iso)
    cutoff_iso = (scan_date - datetime.timedelta(days=window_days)).isoformat()

    min_by_code = {}
    for item in listings:
        code = (item.get('code') or '').strip()
        price = item.get('price')
        last = item.get('last')
        if not code or price is None or price <= 0 or not last or last < cutoff_iso:
            continue
        if not include_facebook and is_facebook(item):
            continue
        prev_min = min_by_code.get(code)
        if prev_min is None or price < prev_min:
            min_by_code[code] = price

    for code, min_price in min_by_code.items():
        pts = history.setdefault(code, [])
        if not pts:
            pts.append([scan_date_iso, min_price])
        elif pts[-1][0] == scan_date_iso:
            pts[-1][1] = min_price
            if len(pts) >= 2 and pts[-2][1] == min_price:
                pts.pop()
        elif pts[-1][1] != min_price:
            pts.append([scan_date_iso, min_price])

        if len(pts) > MAX_HISTORY_POINTS:
            history[code] = pts[-MAX_HISTORY_POINTS:]

    return history


def tr(v):
    """24000000 -> '24tr', 28990000 -> '28,99tr'."""
    return f'{round(v / 1e6, 2):g}'.replace('.', ',') + 'tr'


def build_summary(payload, max_lines=12):
    """Chữ thuần cho Phím tắt iPhone: giá thấp nhất từng cấu hình (ưu tiên dưới trần) + số deal."""
    t = datetime.datetime.fromisoformat(payload['time'])
    since = (t.date() - datetime.timedelta(days=payload['settings']['windowDays'])).isoformat()
    active = [l for l in payload['listings'] if l.get('price') and (l.get('last') or '') >= since]
    rows, deals = [], 0
    for tg in payload['targets']:
        mine = sorted((l for l in active if l['code'] == tg['code']), key=lambda l: l['price'])
        if not mine:
            continue
        cap = tg.get('cap') or 0
        deals += sum(1 for l in mine if cap and l['price'] <= cap)
        best = mine[0]
        h = payload['history'].get(tg['code']) or []
        d = h[-1][1] - h[-2][1] if len(h) >= 2 else 0
        arrow = f" {'▼' if d < 0 else '▲'}{tr(abs(d))}" if d else ''
        name = f"{tg['chip']} {tg['ram']}/{tg['ssd'] // 1024 if tg['ssd'] >= 1024 else tg['ssd']}{'TB' if tg['ssd'] >= 1024 else ''}"
        under = bool(cap) and best['price'] <= cap
        rows.append((not under, best['price'] / cap if cap else 9, f"{'✅' if under else '•'} {name}: {tr(best['price'])} ({best['source']}){arrow}"))
    rows.sort()
    lines = [f'Giá MacBook · {t:%H:%M %d/%m}'] + [r[2] for r in rows[:max_lines - 3]]
    lines += [f'Deal dưới trần: {deals} tin', 'hienphuong99.github.io/MacbookPrice/#deal']
    return '\n'.join(lines) + '\n'


def build_dataset(log_csv, targets_csv, settings_csv, now_iso, prev_history=None, extra_listings=None):
    settings = parse_settings(settings_csv)
    targets = parse_targets(targets_csv)
    listings = parse_listings(log_csv) + list(extra_listings or [])
    if not settings['includeFacebook']:
        listings = [l for l in listings if not is_facebook(l)]
    scan_date_iso = now_iso[:10]
    history = update_history(
        prev_history,
        listings,
        scan_date_iso,
        window_days=settings['windowDays'],
        include_facebook=settings['includeFacebook'],
    )
    return {
        'time': now_iso,
        'settings': settings,
        'targets': targets,
        'listings': listings,
        'history': history,
    }


def fetch_sheet_csv(sheet_id, tab_name, timeout=30):
    url = (
        f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq'
        f'?tqx=out:csv&headers=1&sheet={urllib.parse.quote(tab_name)}'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'MacbookPriceBot/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode('utf-8')
    if text.lstrip().startswith('<'):
        raise SystemExit(f'Sheet {sheet_id} tab "{tab_name}" chưa chia sẻ công khai hoặc không tồn tại')
    return text


def scan_to_file(log_csv, targets_csv, settings_csv, now_iso, out_path=OUT_PATH, extra_listings=None):
    prev_history = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding='utf-8') as f:
                prev_history = json.load(f).get('history') or {}
        except (OSError, ValueError):
            prev_history = {}

    payload = build_dataset(log_csv, targets_csv, settings_csv, now_iso, prev_history=prev_history, extra_listings=extra_listings)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(parent or '.', 'summary.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(build_summary(payload))
    return out_path, payload


def load_shop_listings(path=os.path.join('data', 'shops.json')):
    """Tin do scan_shops.py tự quét (nếu có)."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get('listings') or []
    except (OSError, ValueError):
        return []


def main():
    now_iso = datetime.datetime.now(VN_TZ).isoformat(timespec='seconds')
    log_csv = fetch_sheet_csv(SHEET_ID, TAB_LOG)
    targets_csv = fetch_sheet_csv(SHEET_ID, TAB_TARGETS)
    settings_csv = fetch_sheet_csv(SHEET_ID, TAB_SETTINGS)
    shops = load_shop_listings()
    out_path, payload = scan_to_file(log_csv, targets_csv, settings_csv, now_iso, out_path=OUT_PATH, extra_listings=shops)
    print(f'+ {len(shops)} shop listings')
    print(
        f'{out_path}: {len(payload["targets"])} targets, '
        f'{len(payload["listings"])} listings, '
        f'{len(payload["history"])} history codes (window={payload["settings"]["windowDays"]}d)'
    )


if __name__ == '__main__':
    main()
