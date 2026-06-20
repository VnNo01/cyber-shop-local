import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.parse
import urllib.request
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "neon_market.db"
CATALOG_PATH = ROOT / "products.json"
SESSION_SECRET = os.getenv("SESSION_SECRET", "local-dev-secret-change-me").encode()
PORT = int(os.getenv("PORT", "5173"))
DEAL_PERCENT = 12

PROVIDERS = {
    "github": {
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "user": "https://api.github.com/user",
        "scope": "read:user user:email",
    },
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "user": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
    },
    "facebook": {
        "authorize": "https://www.facebook.com/v19.0/dialog/oauth",
        "token": "https://graph.facebook.com/v19.0/oauth/access_token",
        "user": "https://graph.facebook.com/me?fields=id,name,email",
        "scope": "email,public_profile",
    },
}


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table, column, definition):
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def load_catalog():
    with CATALOG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def seed_products(conn):
    for product in load_catalog():
        conn.execute(
            """
            INSERT OR IGNORE INTO products (
                id, name, category, tag, price, stock, code, description, type,
                delivery, warranty, rating, sold, featured, specs_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product["id"],
                product["name"],
                product["category"],
                product["tag"],
                int(product["price"]),
                int(product["stock"]),
                product["code"],
                product["description"],
                product.get("type", "physical"),
                product.get("delivery", "Giao nhanh 24h"),
                product.get("warranty", "Bao hanh 6 thang"),
                float(product.get("rating", 4.7)),
                int(product.get("sold", 0)),
                1 if product.get("featured") else 0,
                json.dumps(product.get("specs", []), ensure_ascii=False),
                int(time.time()),
            ),
        )
        conn.execute(
            """
            UPDATE products
            SET name = ?, category = ?, tag = ?, price = ?, code = ?, description = ?,
                type = ?, delivery = ?, warranty = ?, rating = ?, featured = ?,
                specs_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                product["name"],
                product["category"],
                product["tag"],
                int(product["price"]),
                product["code"],
                product["description"],
                product.get("type", "physical"),
                product.get("delivery", "Giao nhanh 24h"),
                product.get("warranty", "Bao hanh 6 thang"),
                float(product.get("rating", 4.7)),
                1 if product.get("featured") else 0,
                json.dumps(product.get("specs", []), ensure_ascii=False),
                int(time.time()),
                product["id"],
            ),
        )


def init_db():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                provider TEXT NOT NULL DEFAULT 'local',
                provider_id TEXT,
                role TEXT NOT NULL DEFAULT 'customer',
                created_at INTEGER NOT NULL
            )
            """
        )
        ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'customer'")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                tag TEXT NOT NULL,
                price INTEGER NOT NULL,
                stock INTEGER NOT NULL,
                code TEXT NOT NULL,
                description TEXT NOT NULL,
                type TEXT NOT NULL,
                delivery TEXT NOT NULL,
                warranty TEXT NOT NULL,
                rating REAL NOT NULL,
                sold INTEGER NOT NULL DEFAULT 0,
                featured INTEGER NOT NULL DEFAULT 0,
                specs_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        seed_products(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                items_json TEXT NOT NULL,
                subtotal INTEGER NOT NULL,
                discount INTEGER NOT NULL,
                shipping INTEGER NOT NULL,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'processing',
                created_at INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )


def json_response(handler, status, payload):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def redirect(handler, location):
    handler.send_response(302)
    handler.send_header("Location", location)
    handler.end_headers()


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if not length:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${base64.b64encode(digest).decode()}"


def verify_password(password, stored):
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def sign(value):
    signature = hmac.new(SESSION_SECRET, value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{signature}"


def unsign(signed_value):
    if not signed_value or "." not in signed_value:
        return None
    value, signature = signed_value.rsplit(".", 1)
    expected = hmac.new(SESSION_SECRET, value.encode(), hashlib.sha256).hexdigest()
    return value if hmac.compare_digest(signature, expected) else None


def set_session(handler, user_id):
    signed = sign(str(user_id))
    handler.send_header("Set-Cookie", f"neon_session={signed}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800")


def clear_session(handler):
    handler.send_header("Set-Cookie", "neon_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")


def current_user_id(handler):
    jar = cookies.SimpleCookie(handler.headers.get("Cookie"))
    morsel = jar.get("neon_session")
    return unsign(morsel.value) if morsel else None


def public_user(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "provider": row["provider"],
        "role": row["role"],
        "createdAt": row["created_at"],
    }


def get_user(user_id):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return public_user(row) if row else None


def get_user_row(user_id):
    if not user_id:
        return None
    with connect_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def next_user_role(conn):
    total = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    return "admin" if total == 0 else "customer"


def product_payload(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "tag": row["tag"],
        "price": row["price"],
        "stock": row["stock"],
        "code": row["code"],
        "description": row["description"],
        "type": row["type"],
        "delivery": row["delivery"],
        "warranty": row["warranty"],
        "rating": row["rating"],
        "sold": row["sold"],
        "featured": bool(row["featured"]),
        "specs": json.loads(row["specs_json"]),
    }


def order_payload(row):
    return {
        "id": row["id"],
        "customerName": row["customer_name"],
        "phone": row["phone"],
        "address": row["address"],
        "paymentMethod": row["payment_method"],
        "items": json.loads(row["items_json"]),
        "subtotal": row["subtotal"],
        "discount": row["discount"],
        "shipping": row["shipping"],
        "total": row["total"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }


def calculate_totals(items):
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    discount = round(subtotal * (DEAL_PERCENT / 100)) if subtotal >= 5_000_000 else 0
    shipping = 0 if subtotal == 0 or subtotal >= 3_000_000 else 35_000
    return subtotal, discount, shipping, max(0, subtotal - discount + shipping)


def create_or_get_oauth_user(provider, provider_id, name, email):
    email = email or f"{provider_id}@{provider}.local"
    with connect_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
            (provider, provider_id),
        ).fetchone()
        if row:
            return row

        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            return row

        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, provider, provider_id, role, created_at)
            VALUES (?, ?, NULL, ?, ?, ?, ?)
            """,
            (name or email.split("@")[0], email, provider, provider_id, next_user_role(conn), int(time.time())),
        )
        return conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()


def env_key(provider, suffix):
    return f"{provider.upper()}_{suffix}"


class NeonHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
        ".css": "text/css",
        ".html": "text/html; charset=utf-8",
    }

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path.strip("/")
        if clean_path in {"", "store"}:
            clean_path = "index.html"
        elif clean_path in {"login", "account", "product", "admin"}:
            clean_path = f"{clean_path}.html"
        return str(ROOT / clean_path)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/me":
            user_id = current_user_id(self)
            user = get_user(user_id) if user_id else None
            json_response(self, 200, {"user": user})
            return
        if path == "/api/products":
            self.handle_get_products()
            return
        if path == "/api/orders":
            self.handle_get_orders()
            return
        if path == "/api/admin/dashboard":
            self.handle_admin_dashboard()
            return
        if path.startswith("/auth/"):
            self.handle_auth(path, urllib.parse.parse_qs(parsed.query))
            return
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/register":
            self.handle_register()
            return
        if parsed.path == "/api/login":
            self.handle_login()
            return
        if parsed.path == "/api/logout":
            self.send_response(200)
            clear_session(self)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
            return
        if parsed.path == "/api/orders":
            self.handle_create_order()
            return
        if parsed.path == "/api/admin/orders/status":
            self.handle_admin_order_status()
            return
        if parsed.path == "/api/admin/products/stock":
            self.handle_admin_product_stock()
            return
        json_response(self, 404, {"error": "Not found"})

    def require_admin(self):
        user = get_user_row(current_user_id(self))
        if not user:
            json_response(self, 401, {"error": "Bạn cần đăng nhập."})
            return None
        if user["role"] != "admin":
            json_response(self, 403, {"error": "Bạn không có quyền quản trị."})
            return None
        return user

    def handle_get_products(self):
        with connect_db() as conn:
            rows = conn.execute("SELECT * FROM products ORDER BY featured DESC, category, name").fetchall()
        json_response(self, 200, {"products": [product_payload(row) for row in rows]})

    def handle_get_orders(self):
        user_id = current_user_id(self)
        if not user_id:
            json_response(self, 401, {"error": "Bạn cần đăng nhập để xem đơn hàng."})
            return

        with connect_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM orders
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        json_response(self, 200, {"orders": [order_payload(row) for row in rows]})

    def handle_create_order(self):
        user_id = current_user_id(self)
        if not user_id:
            json_response(self, 401, {"error": "Bạn cần đăng nhập trước khi thanh toán."})
            return

        try:
            payload = read_json(self)
            customer = payload.get("customer") or {}
            items = payload.get("items") or []
            name = (customer.get("name") or "").strip()
            phone = (customer.get("phone") or "").strip()
            address = (customer.get("address") or "").strip()
            payment_method = (customer.get("paymentMethod") or "cod").strip()

            if len(name) < 2 or len(phone) < 8 or len(address) < 10:
                json_response(self, 400, {"error": "Vui lòng nhập đủ tên, số điện thoại và địa chỉ giao hàng."})
                return
            if not items:
                json_response(self, 400, {"error": "Giỏ hàng đang trống."})
                return

            with connect_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                safe_items = []
                for item in items:
                    product_id = str(item.get("id", ""))[:80]
                    quantity = max(1, int(item.get("quantity", 1)))
                    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
                    if not product:
                        conn.rollback()
                        json_response(self, 400, {"error": f"Sản phẩm {product_id} không tồn tại."})
                        return
                    if quantity > product["stock"]:
                        conn.rollback()
                        json_response(self, 409, {"error": f"{product['name']} chỉ còn {product['stock']} sản phẩm."})
                        return
                    safe_items.append(
                        {
                            "id": product["id"],
                            "name": product["name"],
                            "price": product["price"],
                            "quantity": quantity,
                        }
                    )

                subtotal, discount, shipping, total = calculate_totals(safe_items)
                cursor = conn.execute(
                    """
                    INSERT INTO orders (
                        user_id, customer_name, phone, address, payment_method,
                        items_json, subtotal, discount, shipping, total, status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processing', ?)
                    """,
                    (
                        user_id,
                        name,
                        phone,
                        address,
                        payment_method,
                        json.dumps(safe_items, ensure_ascii=False),
                        subtotal,
                        discount,
                        shipping,
                        total,
                        int(time.time()),
                    ),
                )
                order_id = cursor.lastrowid
                for item in safe_items:
                    conn.execute(
                        "UPDATE products SET stock = stock - ?, sold = sold + ?, updated_at = ? WHERE id = ?",
                        (item["quantity"], item["quantity"], int(time.time()), item["id"]),
                    )
                conn.commit()

            json_response(
                self,
                201,
                {
                    "orderId": order_id,
                    "status": "processing",
                    "subtotal": subtotal,
                    "discount": discount,
                    "shipping": shipping,
                    "total": total,
                },
            )
        except Exception:
            json_response(self, 500, {"error": "Không thể tạo đơn hàng lúc này."})

    def handle_admin_dashboard(self):
        if not self.require_admin():
            return

        with connect_db() as conn:
            orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
            products = conn.execute("SELECT * FROM products ORDER BY stock ASC, name").fetchall()
            user_count = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
            totals = conn.execute(
                """
                SELECT COUNT(*) AS order_count, COALESCE(SUM(total), 0) AS revenue
                FROM orders
                """
            ).fetchone()

        json_response(
            self,
            200,
            {
                "summary": {
                    "orders": totals["order_count"],
                    "revenue": totals["revenue"],
                    "users": user_count,
                    "lowStock": len([product for product in products if product["stock"] <= 10]),
                },
                "orders": [order_payload(row) for row in orders],
                "products": [product_payload(row) for row in products],
            },
        )

    def handle_admin_order_status(self):
        if not self.require_admin():
            return

        try:
            payload = read_json(self)
            order_id = int(payload.get("orderId"))
            status = (payload.get("status") or "").strip()
            allowed = {"processing", "confirmed", "shipping", "completed", "cancelled"}
            if status not in allowed:
                json_response(self, 400, {"error": "Trạng thái đơn hàng không hợp lệ."})
                return
            with connect_db() as conn:
                cursor = conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            if cursor.rowcount == 0:
                json_response(self, 404, {"error": "Không tìm thấy đơn hàng."})
                return
            json_response(self, 200, {"ok": True})
        except Exception:
            json_response(self, 500, {"error": "Không thể cập nhật đơn hàng."})

    def handle_admin_product_stock(self):
        if not self.require_admin():
            return

        try:
            payload = read_json(self)
            product_id = str(payload.get("productId") or "")
            stock = max(0, int(payload.get("stock")))
            price = int(payload.get("price")) if payload.get("price") not in {None, ""} else None
            with connect_db() as conn:
                if price is None:
                    cursor = conn.execute(
                        "UPDATE products SET stock = ?, updated_at = ? WHERE id = ?",
                        (stock, int(time.time()), product_id),
                    )
                else:
                    cursor = conn.execute(
                        "UPDATE products SET stock = ?, price = ?, updated_at = ? WHERE id = ?",
                        (stock, max(0, price), int(time.time()), product_id),
                    )
            if cursor.rowcount == 0:
                json_response(self, 404, {"error": "Không tìm thấy sản phẩm."})
                return
            json_response(self, 200, {"ok": True})
        except Exception:
            json_response(self, 500, {"error": "Không thể cập nhật sản phẩm."})

    def handle_register(self):
        try:
            payload = read_json(self)
            name = (payload.get("name") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            if len(name) < 2 or "@" not in email or len(password) < 6:
                json_response(self, 400, {"error": "Tên, email hoặc mật khẩu chưa hợp lệ."})
                return
            with connect_db() as conn:
                role = next_user_role(conn)
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash, provider, provider_id, role, created_at)
                    VALUES (?, ?, ?, 'local', NULL, ?, ?)
                    """,
                    (name, email, hash_password(password), role, int(time.time())),
                )
                user = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()

            self.send_response(201)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            set_session(self, user["id"])
            self.end_headers()
            self.wfile.write(json.dumps({"user": public_user(user)}).encode("utf-8"))
        except sqlite3.IntegrityError:
            json_response(self, 409, {"error": "Email này đã được đăng ký."})
        except Exception:
            json_response(self, 500, {"error": "Không thể đăng ký lúc này."})

    def handle_login(self):
        try:
            payload = read_json(self)
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            with connect_db() as conn:
                user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if not user or not verify_password(password, user["password_hash"]):
                json_response(self, 401, {"error": "Email hoặc mật khẩu không đúng."})
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            set_session(self, user["id"])
            self.end_headers()
            self.wfile.write(json.dumps({"user": public_user(user)}).encode("utf-8"))
        except Exception:
            json_response(self, 500, {"error": "Không thể đăng nhập lúc này."})

    def handle_auth(self, path, query):
        parts = path.strip("/").split("/")
        if len(parts) < 2 or parts[1] not in PROVIDERS:
            json_response(self, 404, {"error": "Unknown provider"})
            return

        provider = parts[1]
        if len(parts) == 2:
            self.start_oauth(provider)
            return
        if len(parts) == 3 and parts[2] == "callback":
            self.finish_oauth(provider, query)
            return
        json_response(self, 404, {"error": "Unknown auth route"})

    def start_oauth(self, provider):
        client_id = os.getenv(env_key(provider, "CLIENT_ID"))
        client_secret = os.getenv(env_key(provider, "CLIENT_SECRET"))
        if not client_id or not client_secret:
            user = create_or_get_oauth_user(
                provider,
                f"demo-{provider}",
                f"Demo {provider.title()} User",
                f"demo-{provider}@neon.local",
            )
            self.send_response(302)
            set_session(self, user["id"])
            self.send_header("Location", "/account?demo_oauth=1")
            self.end_headers()
            return

        state = secrets.token_urlsafe(16)
        redirect_uri = f"http://localhost:{PORT}/auth/{provider}/callback"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": PROVIDERS[provider]["scope"],
            "state": state,
            "response_type": "code",
        }
        redirect(self, f"{PROVIDERS[provider]['authorize']}?{urllib.parse.urlencode(params)}")

    def finish_oauth(self, provider, query):
        code = query.get("code", [""])[0]
        if not code:
            redirect(self, "/login?oauth_error=missing_code")
            return
        try:
            token = self.exchange_code_for_token(provider, code)
            profile = self.fetch_profile(provider, token)
            provider_id = str(profile.get("id") or profile.get("sub"))
            email = profile.get("email") or f"{provider_id}@{provider}.local"
            name = profile.get("name") or profile.get("login") or email.split("@")[0]
            user = create_or_get_oauth_user(provider, provider_id, name, email)
            self.send_response(302)
            set_session(self, user["id"])
            self.send_header("Location", "/account")
            self.end_headers()
        except Exception:
            redirect(self, "/login?oauth_error=failed")

    def exchange_code_for_token(self, provider, code):
        data = urllib.parse.urlencode(
            {
                "client_id": os.getenv(env_key(provider, "CLIENT_ID")),
                "client_secret": os.getenv(env_key(provider, "CLIENT_SECRET")),
                "code": code,
                "redirect_uri": f"http://localhost:{PORT}/auth/{provider}/callback",
                "grant_type": "authorization_code",
            }
        ).encode()
        request = urllib.request.Request(
            PROVIDERS[provider]["token"],
            data=data,
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["access_token"]

    def fetch_profile(self, provider, token):
        request = urllib.request.Request(
            PROVIDERS[provider]["user"],
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    os.chdir(ROOT)
    init_db()
    print(f"NEON//MARKET backend running at http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), NeonHandler).serve_forever()
