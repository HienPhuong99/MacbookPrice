# Phím tắt iPhone "Giá Mac"

Bấm 1 lần (hoặc nói **"Hey Siri, giá Mac"**) là thấy giá MacBook rẻ nhất của từng cấu hình mục tiêu và số deal dưới giá trần. Dữ liệu tự cập nhật 9:30 sáng mỗi ngày.

## Cách 1 — Phím tắt thuần (không cần cài app, 1 phút)

1. Mở app **Phím tắt** (Shortcuts) → bấm **+** (Phím tắt mới) → đặt tên **Giá Mac**.
2. Thêm tác vụ **"Lấy nội dung của URL"** (*Get Contents of URL*), dán địa chỉ:
   ```
   https://hienphuong99.github.io/MacbookPrice/data/summary.txt
   ```
3. Thêm tác vụ **"Hiển thị kết quả"** (*Show Result*) — nó tự nhận nội dung ở bước 2.
4. Bấm **Xong**. Chạy thử: sẽ hiện kiểu
   ```
   Giá MacBook · 09:30 23/11
   ✅ M1 Pro 32/512: 24tr (Chợ Tốt)
   ✅ Air M4 16/512: 28,59tr (Di Động Việt)
   …
   Deal dưới trần: 96 tin
   ```
   ✅ = đang dưới giá trần bạn đặt trong sheet · ▼/▲ = giá thấp nhất vừa giảm/tăng so với lần đổi trước.

Tuỳ chọn:
- **Siri:** tên phím tắt chính là câu lệnh → "Hey Siri, giá Mac". Muốn Siri đọc to: thay bước 3 bằng **"Đọc văn bản"** (*Speak Text*).
- **Màn hình chính:** giữ phím tắt → Chia sẻ → **Thêm vào MH chính**.
- **Mở web khi cần xem kỹ:** thêm tác vụ **"Mở URL"** `https://hienphuong99.github.io/MacbookPrice/#deal`.
- **Tự báo mỗi sáng:** tab **Tự động hoá** → Thời gian trong ngày 9:45 → Hằng ngày → chạy phím tắt **Giá Mac** (tắt "Hỏi trước khi chạy").

## Cách 2 — Widget trên Màn hình chính (app Scriptable, miễn phí)

1. Cài **Scriptable** từ App Store.
2. Mở Scriptable → **+** → dán toàn bộ nội dung file [`iphone/widget.js`](iphone/widget.js) → đặt tên **Giá Mac**.
3. Ra Màn hình chính → giữ chỗ trống → **+** → Scriptable → chọn cỡ Nhỏ/Vừa/Lớn → giữ widget → Sửa → Script: **Giá Mac**.
4. Bấm widget sẽ mở trang Deal. Widget tự làm mới khoảng 3 giờ/lần.

Script này cũng dùng được trong Phím tắt: tác vụ **"Run Script"** của Scriptable → **Giá Mac** → "Hiển thị kết quả".

## Thêm web vào Màn hình chính (như một app)

Safari → mở https://hienphuong99.github.io/MacbookPrice/ → nút Chia sẻ → **Thêm vào MH chính**. Mở từ biểu tượng sẽ chạy toàn màn hình, giao diện kính kiểu iOS 27, có Sáng/Tối và thanh trượt độ mờ kính trong ⚙︎.
