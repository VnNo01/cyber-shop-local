import http.cookiejar
import json
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "http://localhost:5173"
ROOT = Path(__file__).resolve().parent


def request(path, method="GET", payload=None, opener=None):
    opener = opener or urllib.request.build_opener()
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with opener.open(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def reset_test_data():
    products = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    conn = sqlite3.connect(ROOT / "neon_market.db")
    conn.execute("DELETE FROM orders")
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('orders', 'users')")
    for product in products:
        conn.execute(
            """
            UPDATE products
            SET price = ?, stock = ?, sold = ?, updated_at = strftime('%s','now')
            WHERE id = ?
            """,
            (int(product["price"]), int(product["stock"]), int(product.get("sold", 0)), product["id"]),
        )
    conn.commit()
    conn.close()


def main():
    reset_test_data()
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    status, catalog = request("/api/products")
    assert status == 200 and len(catalog["products"]) == 35
    before = next(item for item in catalog["products"] if item["id"] == "laptop-rog")["stock"]

    email = f"admin{int(time.time())}@neon.local"
    status, register = request(
        "/api/register",
        "POST",
        {"name": "Admin Test", "email": email, "password": "secret123"},
        opener,
    )
    assert status == 201 and register["user"]["role"] == "admin"

    status, order = request(
        "/api/orders",
        "POST",
        {
            "customer": {
                "name": "Admin Test",
                "phone": "0901234567",
                "address": "123 Neon Street, District 1, HCMC",
                "paymentMethod": "cod",
            },
            "items": [{"id": "laptop-rog", "quantity": 1}],
        },
        opener,
    )
    assert status == 201 and order["total"] == 26391200

    status, catalog_after = request("/api/products")
    assert status == 200
    after = next(item for item in catalog_after["products"] if item["id"] == "laptop-rog")["stock"]
    assert after == before - 1

    status, dashboard = request("/api/admin/dashboard", opener=opener)
    assert status == 200 and dashboard["summary"]["orders"] == 1

    status, update = request(
        "/api/admin/orders/status",
        "POST",
        {"orderId": order["orderId"], "status": "confirmed"},
        opener,
    )
    assert status == 200 and update["ok"] is True

    reset_test_data()
    print("smoke test passed: catalog, admin, order, stock, dashboard")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as error:
        raise SystemExit(f"Server is not reachable at {BASE_URL}: {error}") from error
