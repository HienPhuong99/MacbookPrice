import importlib.util
import json
import os
import tempfile
import unittest

SCAN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.github', 'scan.py'))
spec = importlib.util.spec_from_file_location('scan', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

SAMPLE_SETTINGS_CSV = '''"Tham số","Giá trị","Giải thích"
"Giá tối đa được ghi vào Nhật ký (đ)","55.000.000 đ",""
"Ngưỡng giá Deal tốt (đ)","32000000",""
"% thấp hơn giá thấp nhất từng ghi → Deal","0,03",""
"Cửa sổ thống kê (ngày)","14",""
"Tính giá Facebook vào thống kê","",""
"Thư mục Drive lưu ảnh Facebook","https://drive.google.com/drive/folders/PRIVATE_FOLDER",""
'''

SAMPLE_TARGETS_CSV = '''"Mã cấu hình","Dòng chip","Tình trạng cần","RAM (GB)","SSD (GB)","Năm ra mắt","Thứ tự dòng","Màn hình chấp nhận","Giá trần (đ)","Bật"
"M1 Pro | 32GB | 512GB","M1 Pro","Cũ","32","512","2021","1","14, 16","32.000.000 đ","Có"
"Air M4 | 16GB | 512GB","Air M4","Mới","16","512","2025","4","13, 15","32.000.000 đ","Có"
"M2 Max | 64GB | 1024GB","M2 Max","Cũ","64","1024","2023","9","16","60.000.000 đ","Không"
'''

SAMPLE_LOG_CSV = '''"ID tin","Ngày ghi","Lần thấy cuối","Mới nhất","Loại nguồn","Nguồn","Mã cấu hình","Dòng chip","CPU/GPU","RAM (GB)","SSD (GB)","Màn (inch)","Tình trạng","Pin (%)","Cycle","Bảo hành (tháng)","Giá niêm yết (đ)","Giá sau KM (đ)","Khuyến mãi","Người bán","URL","Link profile người bán","Link ảnh (Drive)","Cờ","Ghi chú"
"VD-001","2026-09-21","2026-09-21","Không","Web tự dò","Điện Thoại Vui","VÍ DỤ","M1 Pro","8CPU/14GPU","32","512","14","Cũ đẹp","","","6","28.990.000 đ","28.990.000 đ","","Điện Thoại Vui","https://example.com/vd","https://fb.com/secret_vd","https://drive.google.com/secret_vd","","DÒNG VÍ DỤ"
"TIN-001","2026-09-21","19/10/2026 09:53","Không","Web tự dò","QMac Store","M1 Pro | 32GB | 512GB","M1 Pro","8CPU/14GPU","32","512","14","Cũ đẹp","92%","120","6","26.500.000 đ","26.500.000 đ","","QMac Store","https://qmacstore.com/a","https://fb.com/secret_profile_1","https://drive.google.com/file/d/SECRET_IMG_1","","Cũ"
"TIN-001","26/10/2026 09:51","16/11/2026 09:00","Có","Web tự dò","QMac Store","M1 Pro | 32GB | 512GB","M1 Pro","8CPU/14GPU","32","512","14","Cũ đẹp","95%","80","6","29.500.000 đ","25.500.000 đ","Giảm 4tr","QMac Store","https://qmacstore.com/a","https://fb.com/secret_profile_2","https://drive.google.com/file/d/SECRET_IMG_2","","Bản mới nhất"
"TIN-002","2026-09-21","9/11/2026 09:00","Có","Web tự dò","MacVN","M1 Pro | 32GB | 512GB","M1 Pro","10CPU/16GPU","32","512","16","Cũ đẹp","","","6","28.990.000 đ","28.990.000 đ","","MacVN","https://macvn.com.vn/b","","https://drive.google.com/file/d/SECRET_IMG_3","",""
"TIN-003","2026-09-21","2026-10-01","Không","Web tự dò","Shop Cũ","M1 Pro | 32GB | 512GB","M1 Pro","8CPU/14GPU","32","512","14","Cũ đẹp","","","","20.000.000 đ","20.000.000 đ","","Shop Cũ","https://example.com/old","","","","Quá hạn 14 ngày"
"TIN-004","16/11/2026 09:00","16/11/2026 09:00","Có","Facebook","Facebook Group","M1 Pro | 32GB | 512GB","M1 Pro","8CPU/14GPU","32","512","14","Cũ đẹp","","","","18.000.000 đ","18.000.000 đ","","Inbox","https://fb.com/post/1","https://fb.com/secret_fb","https://drive.google.com/secret_fb","","Giá câu inbox"
'''


class ScanMacbookTest(unittest.TestCase):
    def test_parse_price_and_numbers(self):
        self.assertEqual(scan.parse_int('28.990.000 đ'), 28990000)
        self.assertEqual(scan.parse_int('32.000.000 đ'), 32000000)
        self.assertEqual(scan.parse_int('32000000'), 32000000)
        self.assertEqual(scan.parse_int('95%'), 95)
        self.assertAlmostEqual(scan.parse_num('0,03'), 0.03)
        self.assertIsNone(scan.parse_int(''))
        self.assertIsNone(scan.parse_int('256GB'))

    def test_parse_two_date_formats(self):
        self.assertEqual(scan.parse_date_iso('2026-09-21'), '2026-09-21')
        self.assertEqual(scan.parse_date_iso('19/10/2026 09:53'), '2026-10-19')
        self.assertEqual(scan.parse_date_iso('9/11/2026 09:00'), '2026-11-09')
        self.assertIsNone(scan.parse_date_iso('31/02/2026'))
        self.assertIsNone(scan.parse_date_iso(''))

    def test_listings_dedup_skip_vd_and_privacy(self):
        listings = scan.parse_listings(SAMPLE_LOG_CSV)
        ids = [x['id'] for x in listings]
        self.assertNotIn('VD-001', ids)
        self.assertEqual(ids.count('TIN-001'), 1)

        tin1 = next(x for x in listings if x['id'] == 'TIN-001')
        # Giữ dòng cuối của TIN-001
        self.assertEqual(tin1['first'], '2026-10-26')
        self.assertEqual(tin1['last'], '2026-11-16')
        self.assertTrue(tin1['latest'])
        self.assertEqual(tin1['list'], 29500000)
        self.assertEqual(tin1['price'], 25500000)
        self.assertEqual(tin1['battery'], 95)
        self.assertEqual(tin1['cycle'], 80)
        self.assertEqual(tin1['note'], 'Bản mới nhất')

        tin2 = next(x for x in listings if x['id'] == 'TIN-002')
        self.assertIsNone(tin2['battery'])
        self.assertIsNone(tin2['cycle'])

        # Không lộ 2 cột riêng tư
        dumped = json.dumps(listings, ensure_ascii=False)
        for secret in ('secret_vd', 'secret_profile_1', 'secret_profile_2', 'SECRET_IMG_1', 'SECRET_IMG_2', 'SECRET_IMG_3', 'secret_fb'):
            self.assertNotIn(secret, dumped)
        for item in listings:
            self.assertNotIn('profile', item)
            self.assertNotIn('image', item)

    def test_marketplace_seller_hidden_and_facebook_dropped(self):
        row = '"TIN-009","16/11/2026","16/11/2026","Có","Web tự dò","Chợ Tốt","M1 Pro | 32GB | 512GB","M1 Pro","","32","512","14","Cũ","","","","24.000.000 đ","24.000.000 đ","","Nguyễn Văn A","https://www.chotot.com/1.htm","","","",""\n'
        tin9 = next(x for x in scan.parse_listings(SAMPLE_LOG_CSV + row) if x['id'] == 'TIN-009')
        self.assertEqual(tin9['seller'], '')
        data = scan.build_dataset(SAMPLE_LOG_CSV, SAMPLE_TARGETS_CSV, SAMPLE_SETTINGS_CSV, '2026-11-22T09:30:00+07:00')
        self.assertNotIn('TIN-004', [x['id'] for x in data['listings']])

    def test_targets_filters_disabled(self):
        targets = scan.parse_targets(SAMPLE_TARGETS_CSV)
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0]['code'], 'M1 Pro | 32GB | 512GB')
        self.assertEqual(targets[0]['screens'], [14, 16])
        self.assertEqual(targets[0]['cap'], 32000000)
        self.assertEqual(targets[0]['order'], 1)

    def test_history_tracks_window_and_changes_only(self):
        listings = scan.parse_listings(SAMPLE_LOG_CSV)
        code = 'M1 Pro | 32GB | 512GB'

        # TIN-003 (20tr) quá hạn 14 ngày; TIN-004 (18tr) là Facebook mặc định loại -> min là TIN-001 = 25.5tr
        h1 = scan.update_history({}, listings, '2026-11-22', window_days=14, include_facebook=False)
        self.assertEqual(h1[code], [['2026-11-22', 25500000]])

        # Ngày hôm sau giá không đổi -> không thêm điểm thừa
        h2 = scan.update_history(h1, listings, '2026-11-23', window_days=14, include_facebook=False)
        self.assertEqual(h2[code], [['2026-11-22', 25500000]])

        # Ngày hôm sau nữa giá giảm -> thêm điểm mới
        cheaper = [dict(x, price=24000000) if x['id'] == 'TIN-001' else x for x in listings]
        h3 = scan.update_history(h2, cheaper, '2026-11-24', window_days=14, include_facebook=False)
        self.assertEqual(h3[code], [['2026-11-22', 25500000], ['2026-11-24', 24000000]])

        # Quét lại cùng ngày 2026-11-24 với giá mới -> ghi đè cùng ngày
        even_cheaper = [dict(x, price=23500000) if x['id'] == 'TIN-001' else x for x in listings]
        h4 = scan.update_history(h3, even_cheaper, '2026-11-24', window_days=14, include_facebook=False)
        self.assertEqual(h4[code], [['2026-11-22', 25500000], ['2026-11-24', 23500000]])

        # Quét lại cùng ngày 2026-11-24 quay về đúng giá trước đó -> gộp bỏ điểm thừa
        h5 = scan.update_history(h4, listings, '2026-11-24', window_days=14, include_facebook=False)
        self.assertEqual(h5[code], [['2026-11-22', 25500000]])

    def test_scan_to_file_preserves_history_and_privacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, 'macbook.json')
            _, d1 = scan.scan_to_file(
                SAMPLE_LOG_CSV, SAMPLE_TARGETS_CSV, SAMPLE_SETTINGS_CSV,
                '2026-11-22T09:30:00+07:00', out_path=out_path,
            )
            self.assertEqual(d1['time'], '2026-11-22T09:30:00+07:00')
            self.assertEqual(d1['settings']['windowDays'], 14)

            with open(out_path, encoding='utf-8') as f:
                raw_text = f.read()
            self.assertNotIn('PRIVATE_FOLDER', raw_text)
            self.assertNotIn('secret_profile_1', raw_text)
            self.assertNotIn('SECRET_IMG_1', raw_text)

            # Lần quét ngày sau với giá mới -> nối tiếp history cũ
            updated_log = SAMPLE_LOG_CSV.replace('25.500.000 đ', '24.500.000 đ')
            _, d2 = scan.scan_to_file(
                updated_log, SAMPLE_TARGETS_CSV, SAMPLE_SETTINGS_CSV,
                '2026-11-23T09:30:00+07:00', out_path=out_path,
            )
            self.assertEqual(
                d2['history']['M1 Pro | 32GB | 512GB'],
                [['2026-11-22', 25500000], ['2026-11-23', 24500000]],
            )


if __name__ == '__main__':
    unittest.main()
