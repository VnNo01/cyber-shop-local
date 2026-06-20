let product = null;
const detail = document.querySelector("#productDetail");
const toast = document.querySelector("#toast");
const cartCount = document.querySelector("#cartCount");
const money = new Intl.NumberFormat("vi-VN").format;

function formatCurrency(value) {
  return `${money(value)}d`;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 1900);
}

function getCart() {
  return JSON.parse(localStorage.getItem("neon-market-cart") || "{}");
}

function saveCart(cart) {
  localStorage.setItem("neon-market-cart", JSON.stringify(cart));
}

function updateCartCount() {
  const count = Object.values(getCart()).reduce((sum, quantity) => sum + quantity, 0);
  cartCount.textContent = count;
}

function addToCart(redirect = false) {
  if (!product || product.stock <= 0) return;
  const cart = getCart();
  const current = cart[product.id] || 0;
  if (current >= product.stock) {
    showToast("Sản phẩm đã đạt giới hạn tồn kho.");
    return;
  }
  cart[product.id] = current + 1;
  saveCart(cart);
  updateCartCount();
  if (redirect) {
    window.location.href = "/?openCart=1";
    return;
  }
  showToast(`Đã thêm ${product.name}`);
}

function renderProduct() {
  document.title = `${product.name} - NEON//MARKET`;
  detail.innerHTML = `
    <section class="product-detail">
      <div class="product-hero-art">
        <span>${product.code}</span>
      </div>
      <article class="product-info-panel">
        <p class="eyebrow">${product.tag}</p>
        <h1>${product.name}</h1>
        <p class="hero-text">${product.description}</p>
        <div class="product-proof detail-proof">
          <span>${product.rating} sao</span>
          <span>Đã bán ${product.sold}</span>
          <span>${product.stock > 0 ? `Còn ${product.stock}` : "Hết hàng"}</span>
        </div>
        <strong class="detail-price">${formatCurrency(product.price)}</strong>
        <div class="detail-actions">
          <button class="primary-btn" id="buyNow" type="button" ${product.stock <= 0 ? "disabled" : ""}>Mua ngay</button>
          <button class="ghost-btn" id="addToCart" type="button" ${product.stock <= 0 ? "disabled" : ""}>Thêm vào giỏ</button>
        </div>
        <section class="detail-specs">
          <h2>Thông tin bán hàng</h2>
          <ul>
            ${product.specs.map((spec) => `<li>${spec}</li>`).join("")}
            <li>Giao dịch được lưu đơn trong database local.</li>
            <li>Server kiểm tra giá và tồn kho khi thanh toán.</li>
          </ul>
        </section>
      </article>
    </section>
  `;

  document.querySelector("#addToCart").addEventListener("click", () => addToCart(false));
  document.querySelector("#buyNow").addEventListener("click", () => addToCart(true));
}

async function loadProduct() {
  updateCartCount();
  const id = new URLSearchParams(window.location.search).get("id");
  const response = await fetch("/api/products");
  const data = await response.json();
  product = data.products.find((item) => item.id === id);
  if (!product) {
    detail.innerHTML = `<section class="empty-state">Không tìm thấy sản phẩm.</section>`;
    return;
  }
  renderProduct();
}

loadProduct();
