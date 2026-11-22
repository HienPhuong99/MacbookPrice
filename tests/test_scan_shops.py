import importlib.util
import os
import sys
import unittest

GH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.github'))
sys.path.insert(0, GH)
spec = importlib.util.spec_from_file_location('scan_shops', os.path.join(GH, 'scan_shops.py'))
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

TARGETS = [
    {'code': 'M1 Pro | 32GB | 512GB', 'chip': 'M1 Pro', 'need': 'Cũ', 'ram': 32, 'ssd': 512, 'screens': [14, 16]},
    {'code': 'M1 Max | 64GB | 1024GB', 'chip': 'M1 Max', 'need': 'Cũ', 'ram': 64, 'ssd': 1024, 'screens': [14, 16]},
    {'code': 'Air M4 | 16GB | 512GB', 'chip': 'Air M4', 'need': 'Mới', 'ram': 16, 'ssd': 512, 'screens': [13, 15]},
    {'code': 'M4 | 32GB | 512GB', 'chip': 'M4', 'need': 'Cả hai', 'ram': 32, 'ssd': 512, 'screens': [13, 14, 15]},
]


class ShopScanTest(unittest.TestCase):
    def code(self, title, extra=''):
        p = ss.parse_title(title, extra)
        t = p and ss.match_target(p, TARGETS)
        return t and t['code']

    def test_titles_from_real_shops(self):
        self.assertEqual(self.code('Macbook Pro 14 inch - M1 Max 10 CPU/ 24GPU/ 64Gb/ 1Tb - Likenew'), 'M1 Max | 64GB | 1024GB')
        self.assertEqual(self.code('Macbook Pro 16 - M1 PRO 10CPU-16GPU / 32Gb / 512GB - 2021 - Likenew'), 'M1 Pro | 32GB | 512GB')
        self.assertEqual(self.code('MacBook Air 13 inch M4 10CPU/10GPU 16GB/512GB - Newseal'), 'Air M4 | 16GB | 512GB')
        self.assertEqual(self.code('MacBook Air 15 inch M4 32GB/512GB Mới 100%'), 'M4 | 32GB | 512GB')  # "M4" nhận cả Air M4

    def test_rejects_wrong_condition_screen_or_missing_specs(self):
        self.assertIsNone(self.code('Macbook Air 13 inch M4 16GB/512GB - Likenew 99%'))   # cần Mới
        self.assertIsNone(self.code('MacBook Pro 13 inch M1 Pro 32GB 512GB'))             # màn 13 không chấp nhận
        self.assertIsNone(self.code('MacBook Pro 14 M1 Pro'))                              # thiếu RAM/SSD
        self.assertIsNone(self.code('iPad Pro M4 16GB 512GB'))                             # không phải MacBook

    def test_scan_dedups_keeps_first_and_survives_shop_error(self):
        raw = [{'id': '1', 'title': 'Macbook Pro 14 M1 Pro 32GB 512GB Likenew', 'extra': '', 'price': 24_000_000, 'list': None, 'url': 'https://x/1'}]
        def boom(shop):
            raise OSError('down')
        prev = {'listings': [{'id': 'SHOP-MacShop24h-1', 'first': '2026-11-01'}]}
        d = ss.scan_shops(TARGETS, '2026-11-22', prev, fetchers={'sapo': lambda s: raw, 'woo': boom})
        mine = [l for l in d['listings'] if l['source'] == 'MacShop24h']
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]['first'], '2026-11-01')
        self.assertEqual(mine[0]['last'], '2026-11-22')
        self.assertTrue(d['report']['MacVN'].startswith('LỖI'))


if __name__ == '__main__':
    unittest.main()
