# NEON//MARKET

NEON//MARKET là website bán hàng local phong cách cyber/cyborg. Dự án có frontend HTML/CSS/JavaScript, backend Python thuần, database SQLite, giỏ hàng, checkout, tài khoản khách hàng và trang admin.

## Tính năng chính

- Catalog sản phẩm đọc từ API `/api/products`, seed từ `products.json` vào SQLite.
- Lọc sản phẩm realtime theo tên, danh mục và giá.
- Giỏ hàng lưu bằng `localStorage`, checkout có thông tin nhận hàng và phương thức thanh toán.
- Backend kiểm tra giá/tồn kho khi đặt hàng, tạo đơn và trừ tồn kho.
- Đăng ký/đăng nhập local; user đầu tiên tự động là `admin`.
- Admin console xem doanh thu, đơn hàng, tồn kho, đổi trạng thái đơn, chỉnh stock/giá.
- OAuth Google/Facebook/GitHub có chế độ demo; có thể cấu hình app thật bằng biến môi trường.
- Giao diện responsive cho desktop và mobile.

## Cấu trúc

```text
.
├── server.py              # Backend HTTP + SQLite + auth + API
├── products.json          # Catalog seed ban đầu
├── smoke_test.py          # Kiểm thử nhanh API và luồng đặt hàng
├── index.html / app.js    # Trang cửa hàng
├── product.html / product.js
├── login.html / auth.js / auth.css
├── account.html / account.js
├── admin.html / admin.js
└── styles.css
```

## Chạy local

```powershell
cd cyber-shop-local
python server.py
```

Mở trình duyệt tại:

```text
http://localhost:5173
```

Các trang chính:

- Cửa hàng: `http://localhost:5173`
- Đăng nhập/đăng ký: `http://localhost:5173/login`
- Hồ sơ tài khoản: `http://localhost:5173/account`
- Admin console: `http://localhost:5173/admin`

Database local được tạo tại `neon_market.db` và đã được ignore khỏi Git.

## Kiểm thử nhanh

Khi server đang chạy, mở terminal khác:

```powershell
python smoke_test.py
```

Script kiểm tra catalog, đăng ký admin, tạo đơn, trừ tồn kho, admin dashboard, đổi trạng thái đơn rồi tự reset dữ liệu test.

## OAuth thật

Nếu muốn dùng OAuth provider thật, tạo app trong từng provider rồi đặt biến môi trường trước khi chạy server:

```powershell
$env:GITHUB_CLIENT_ID="..."
$env:GITHUB_CLIENT_SECRET="..."
$env:GOOGLE_CLIENT_ID="..."
$env:GOOGLE_CLIENT_SECRET="..."
$env:FACEBOOK_CLIENT_ID="..."
$env:FACEBOOK_CLIENT_SECRET="..."
python server.py
```

Callback URL:

```text
http://localhost:5173/auth/github/callback
http://localhost:5173/auth/google/callback
http://localhost:5173/auth/facebook/callback
```

## Ghi chú

- `SESSION_SECRET` mặc định chỉ phù hợp local dev; khi demo nghiêm túc nên đặt biến môi trường riêng.
- Không commit `neon_market.db`, `.env` hoặc secret OAuth thật.
