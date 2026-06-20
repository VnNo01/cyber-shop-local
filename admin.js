const summaryEl = document.querySelector("#adminSummary");
const ordersSection = document.querySelector("#ordersSection");
const productsSection = document.querySelector("#productsSection");
const toast = document.querySelector("#toast");
const money = new Intl.NumberFormat("vi-VN").format;

function formatCurrency(value) {
  return `${money(value)}d`;
}

function formatDate(timestamp) {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp * 1000));
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 1900);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (response.status === 401) {
    window.location.href = "/login";
    return null;
  }
  if (!response.ok) throw new Error(data.error || "Có lỗi xảy ra.");
  return data;
}

function renderSummary(summary) {
  summaryEl.innerHTML = `
    <article><span>Đơn hàng</span><strong>${summary.orders}</strong></article>
    <article><span>Doanh thu</span><strong>${formatCurrency(summary.revenue)}</strong></article>
    <article><span>Người dùng</span><strong>${summary.users}</strong></article>
    <article><span>Sắp hết hàng</span><strong>${summary.lowStock}</strong></article>
  `;
}

function renderOrders(orders) {
  ordersSection.innerHTML = `
    <div class="section-title">
      <div>
        <p class="eyebrow">Orders</p>
        <h2>Đơn hàng mới nhất</h2>
      </div>
    </div>
    <div class="admin-table">
      ${orders.length ? orders.map((order) => `
        <article class="admin-row">
          <div>
            <strong>#${order.id} - ${formatCurrency(order.total)}</strong>
            <span>${order.customerName} / ${order.phone}</span>
            <span>${formatDate(order.createdAt)}</span>
          </div>
          <select data-order-status="${order.id}">
            ${["processing", "confirmed", "shipping", "completed", "cancelled"]
              .map((status) => `<option value="${status}" ${status === order.status ? "selected" : ""}>${status}</option>`)
              .join("")}
          </select>
        </article>
      `).join("") : `<article class="empty-state">Chưa có đơn hàng.</article>`}
    </div>
  `;
}

function renderProducts(products) {
  productsSection.innerHTML = `
    <div class="section-title">
      <div>
        <p class="eyebrow">Inventory</p>
        <h2>Tồn kho và giá</h2>
      </div>
    </div>
    <div class="admin-table">
      ${products.map((product) => `
        <article class="admin-row">
          <div>
            <strong>${product.name}</strong>
            <span>${product.tag} / đã bán ${product.sold}</span>
            <span>${formatCurrency(product.price)}</span>
          </div>
          <div class="inventory-controls">
            <input type="number" min="0" value="${product.stock}" aria-label="Tồn kho ${product.name}" data-stock="${product.id}" />
            <input type="number" min="0" step="1000" value="${product.price}" aria-label="Giá ${product.name}" data-price="${product.id}" />
            <button class="add-btn" type="button" data-save-product="${product.id}">Lưu</button>
          </div>
        </article>
      `).join("")}
    </div>
  `;
}

async function loadDashboard() {
  summaryEl.innerHTML = `<article><span>Đang tải</span><strong>...</strong></article>`;
  try {
    const data = await api("/api/admin/dashboard");
    if (!data) return;
    renderSummary(data.summary);
    renderOrders(data.orders);
    renderProducts(data.products);
  } catch (error) {
    summaryEl.innerHTML = `<article><span>Lỗi</span><strong>${error.message}</strong></article>`;
    ordersSection.innerHTML = "";
    productsSection.innerHTML = "";
  }
}

document.addEventListener("change", async (event) => {
  const orderId = event.target.dataset.orderStatus;
  if (!orderId) return;
  try {
    await api("/api/admin/orders/status", {
      method: "POST",
      body: JSON.stringify({ orderId, status: event.target.value }),
    });
    showToast(`Đã cập nhật đơn #${orderId}`);
    await loadDashboard();
  } catch (error) {
    showToast(error.message);
  }
});

document.addEventListener("click", async (event) => {
  const productId = event.target.dataset.saveProduct;
  if (!productId) return;
  const stock = document.querySelector(`[data-stock="${productId}"]`).value;
  const price = document.querySelector(`[data-price="${productId}"]`).value;
  try {
    await api("/api/admin/products/stock", {
      method: "POST",
      body: JSON.stringify({ productId, stock, price }),
    });
    showToast("Đã lưu sản phẩm.");
    await loadDashboard();
  } catch (error) {
    showToast(error.message);
  }
});

loadDashboard();
