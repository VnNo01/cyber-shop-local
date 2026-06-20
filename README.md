# NEON//MARKET

Trang web bán hàng local phong cách cyber/cyborg với:

- Lọc sản phẩm real time theo tên, danh mục và giá.
- Danh mục hàng đa dạng: laptop, tài khoản game, gaming, techwear, âm thanh, smart home, wearable, di chuyển, bảo mật và phụ kiện.
- Giỏ hàng cập nhật tức thì, lưu bằng `localStorage`.
- Deal giảm giá, đếm ngược và thanh toán mô phỏng.
- Checkout có tên người nhận, số điện thoại, địa chỉ, phương thức thanh toán.
- Backend lưu đơn hàng vào SQLite và trang tài khoản hiển thị lịch sử đơn.
- Catalog sản phẩm được seed vào SQLite từ `products.json`, frontend đọc qua `/api/products`.
- Server tự kiểm giá/tồn kho khi đặt hàng và trừ kho sau khi tạo đơn.
- User đầu tiên đăng ký sẽ là `admin` và có thể mở `/admin` để xem doanh thu, đơn hàng, tồn kho, đổi trạng thái đơn, chỉnh stock/giá.
- Giao diện responsive cho desktop và mobile.

## Chạy local có backend

Chạy server Python để có cả frontend, backend API và database SQLite:

```powershell
cd cyber-shop-local
python server.py
```

Sau đó mở:

```text
http://localhost:5173
```

Các trang chính:

- Cửa hàng: `http://localhost:5173`
- Chi tiết sản phẩm: bấm `Chi tiết` trên từng sản phẩm
- Đăng nhập/đăng ký: `http://localhost:5173/login`
- Hồ sơ tài khoản: `http://localhost:5173/account`
- Admin console: `http://localhost:5173/admin`

Tài khoản và đơn hàng được lưu trong file `neon_market.db`.

## Kiểm thử nhanh

Khi server đang chạy, mở terminal khác:

```powershell
python smoke_test.py
```

Script này kiểm tra catalog, đăng ký admin, tạo đơn, trừ tồn kho, admin dashboard, đổi trạng thái đơn rồi tự reset dữ liệu test.

## OAuth Google/Facebook/GitHub

Các nút OAuth chạy được ngay ở chế độ demo nếu chưa cấu hình app thật. Khi muốn dùng OAuth thật, tạo app trong từng provider và đặt biến môi trường trước khi chạy:

```powershell
$env:GITHUB_CLIENT_ID="..."
$env:GITHUB_CLIENT_SECRET="..."
$env:GOOGLE_CLIENT_ID="..."
$env:GOOGLE_CLIENT_SECRET="..."
$env:FACEBOOK_CLIENT_ID="..."
$env:FACEBOOK_CLIENT_SECRET="..."
python server.py
```

Callback URL cần khai báo với provider:

```text
http://localhost:5173/auth/github/callback
http://localhost:5173/auth/google/callback
http://localhost:5173/auth/facebook/callback
```
