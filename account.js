const accountGrid = document.querySelector("#accountGrid");
const orderList = document.querySelector("#orderList");
const logoutBtn = document.querySelector("#logoutBtn");
const toast = document.querySelector("#toast");
const money = new Intl.NumberFormat("vi-VN").format;

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

function formatCurrency(value) {
  return `${money(value)}d`;
}

function paymentLabel(value) {
  return {
    cod: "COD khi nhận hàng",
    bank: "Chuyển khoản ngân hàng",
    wallet: "Ví điện tử",
  }[value] || value;
}

async function loadAccount() {
  const response = await fetch("/api/me");
  const data = await response.json();
  if (!data.user) {
    window.location.href = "/login";
    return;
  }

  const demoNote = new URLSearchParams(window.location.search).has("demo_oauth")
    ? `<div class="account-row"><span>Ghi chú OAuth</span><strong>Đang dùng chế độ demo vì chưa cấu hình client id/secret.</strong></div>`
    : "";

  accountGrid.innerHTML = `
    <div class="account-row"><span>Tên</span><strong>${data.user.name}</strong></div>
    <div class="account-row"><span>Email</span><strong>${data.user.email}</strong></div>
    <div class="account-row"><span>Kiểu đăng nhập</span><strong>${data.user.provider}</strong></div>
    <div class="account-row"><span>Vai trò</span><strong>${data.user.role}</strong></div>
    <div class="account-row"><span>Ngày tạo</span><strong>${formatDate(data.user.createdAt)}</strong></div>
    ${demoNote}
    ${data.user.role === "admin" ? `<div class="account-row"><span>Quản trị</span><strong><a href="/admin">Mở admin console</a></strong></div>` : ""}
  `;

  await loadOrders();
}

async function loadOrders() {
  orderList.innerHTML = `<div class="skeleton"></div>`;
  const response = await fetch("/api/orders");
  if (!response.ok) {
    orderList.innerHTML = "";
    return;
  }

  const data = await response.json();
  if (!data.orders.length) {
    orderList.innerHTML = `
      <article class="order-card">
        <header>
          <h3>Chưa có đơn hàng</h3>
          <span class="order-status">new</span>
        </header>
        <p class="auth-copy">Khi bạn đặt hàng, đơn sẽ được lưu vào database và xuất hiện tại đây.</p>
      </article>
    `;
    return;
  }

  orderList.innerHTML = `
    <p class="eyebrow">Order history</p>
    ${data.orders
      .map(
        (order) => `
          <article class="order-card">
            <header>
              <h3>Đơn #${order.id}</h3>
              <span class="order-status">${order.status}</span>
            </header>
            <div class="account-row"><span>Ngày đặt</span><strong>${formatDate(order.createdAt)}</strong></div>
            <div class="account-row"><span>Người nhận</span><strong>${order.customerName} - ${order.phone}</strong></div>
            <div class="account-row"><span>Địa chỉ</span><strong>${order.address}</strong></div>
            <div class="account-row"><span>Thanh toán</span><strong>${paymentLabel(order.paymentMethod)}</strong></div>
            <ul>
              ${order.items.map((item) => `<li>${item.name} x ${item.quantity} - ${formatCurrency(item.price * item.quantity)}</li>`).join("")}
            </ul>
            <footer>
              <span>Tổng thanh toán</span>
              <strong>${formatCurrency(order.total)}</strong>
            </footer>
          </article>
        `,
      )
      .join("")}
  `;
}

logoutBtn.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  showToast("Đã đăng xuất.");
  window.setTimeout(() => {
    window.location.href = "/login";
  }, 600);
});

loadAccount();
