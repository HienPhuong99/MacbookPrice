# Dò giá MacBook

Web theo dõi giá MacBook (mới & cũ) theo cấu hình mục tiêu, giao diện kính kiểu iOS 27, có Phím tắt iPhone.

- **Web:** https://hienphuong99.github.io/MacbookPrice/ — Safari → Chia sẻ → Thêm vào MH chính.
- **Phím tắt iPhone:** xem [HUONG-DAN-PHIM-TAT.md](HUONG-DAN-PHIM-TAT.md) (2 tác vụ, không cần app) · widget Scriptable: [`iphone/widget.js`](iphone/widget.js).
- **Dữ liệu:** GitHub Actions 9:30 & 21:30 mỗi ngày → `.github/scan_shops.py` (tự quét shop có JSON + Chợ Tốt) + `.github/scan.py` (Google Sheet "Dò giá MacBook 2027") → `data/macbook.json`, `data/summary.txt`, `data/menu.json` (Phím tắt "Chọn Mac"); deal mới báo qua ntfy.

Kiểm tra: `python -m unittest discover tests` · `node iphone/widget.js`
