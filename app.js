let products = [];
const state = {
  cart: JSON.parse(localStorage.getItem("neon-market-cart") || "{}"),
  dealPercent: 12,
  dealEndsIn: 14 * 60 + 59,
};

const money = new Intl.NumberFormat("vi-VN").format;
const productGrid = document.querySelector("#productGrid");
const storefrontSections = document.querySelector("#featuredSections");
const cartDrawer = document.querySelector("#cartDrawer");
const cartItems = document.querySelector("#cartItems");
const cartEmpty = document.querySelector("#cartEmpty");
const cartCount = document.querySelector("#cartCount");
const searchInput = document.querySelector("#searchInput");
const categoryFilter = document.querySelector("#categoryFilter");
const priceRange = document.querySelector("#priceRange");
const priceValue = document.querySelector("#priceValue");
const dealPercent = document.querySelector("#dealPercent");
const dealTimer = document.querySelector("#dealTimer");
const toast = document.querySelector("#toast");
const accountLink = document.querySelector("#accountLink");
const checkoutForm = document.querySelector("#checkoutForm");

function formatCurrency(value) {
  return `${money(value)}d`;
}

function originalPrice(product) {
  const multiplier = product.category === "game-account" ? 1.82 : product.category === "laptop" ? 1.18 : 1.34;
  return Math.ceil((product.price * multiplier) / 10000) * 10000;
}

function discountPercent(product) {
  const original = originalPrice(product);
  return Math.max(8, Math.round(((original - product.price) / original) * 100));
}

function badgeText(product) {
  if (product.category === "game-account") return "Bàn giao nhanh";
  if (product.category === "laptop") return "Bảo hành thật";
  if (product.category === "gaming") return "Gaming hot";
  if (product.type === "digital") return "Digital";
  return "Sẵn kho";
}

function renderProductCard(product, variant = "") {
  return `
    <article class="product-card ${variant}">
      <a class="product-art" href="/product?id=${encodeURIComponent(product.id)}" aria-label="Xem ${product.name}">
        <span>${product.code}</span>
        <b>${badgeText(product)}</b>
      </a>
      <div class="tag-row">
        <span class="tag">${product.tag}</span>
        <span class="stock">${product.stock > 0 ? `Còn ${product.stock}` : "Hết hàng"}</span>
      </div>
      <h3>${product.name}</h3>
      <p>${product.description}</p>
      <div class="product-proof">
        <span>${product.rating} sao</span>
        <span>Đã bán ${product.sold}</span>
        <span>${product.delivery}</span>
      </div>
      <div class="price-stack">
        <span class="price">${formatCurrency(product.price)}</span>
        <span class="old-price">${formatCurrency(originalPrice(product))}</span>
        <strong>-${discountPercent(product)}%</strong>
      </div>
      <div class="card-foot">
        <a class="detail-link" href="/product?id=${encodeURIComponent(product.id)}">Chi tiết</a>
        <button class="add-btn" type="button" data-add="${product.id}" ${product.stock <= 0 ? "disabled" : ""}>Thêm</button>
      </div>
    </article>
  `;
}

function saveCart() {
  localStorage.setItem("neon-market-cart", JSON.stringify(state.cart));
}

function filteredProducts() {
  const keyword = searchInput.value.trim().toLowerCase();
  const category = categoryFilter.value;
  const maxPrice = Number(priceRange.value);

  return products.filter((product) => {
    const matchesKeyword = `${product.name} ${product.description} ${product.tag}`.toLowerCase().includes(keyword);
    const matchesCategory = category === "all" || product.category === category;
    return matchesKeyword && matchesCategory && product.price <= maxPrice;
  });
}

function renderProducts() {
  const items = filteredProducts();
  priceValue.textContent = formatCurrency(Number(priceRange.value));

  if (!products.length) {
    productGrid.innerHTML = `<div class="empty-state">Đang tải kho hàng từ backend...</div>`;
    return;
  }

  if (!items.length) {
    productGrid.innerHTML = `<div class="empty-state">Không tìm thấy sản phẩm phù hợp với bộ lọc hiện tại.</div>`;
    return;
  }

  productGrid.innerHTML = items.map((product) => renderProductCard(product)).join("");
}

function sectionItems(predicate, limit = 4) {
  return products
    .filter(predicate)
    .sort((a, b) => Number(b.featured) - Number(a.featured) || b.sold - a.sold)
    .slice(0, limit);
}

function renderStorefrontSections() {
  if (!storefrontSections) return;
  if (!products.length) {
    storefrontSections.innerHTML = `<div class="empty-state">Đang nạp các kệ hàng nổi bật...</div>`;
    return;
  }

  const sections = [
    {
      eyebrow: "Digital delivery",
      title: "Tài khoản game & key đang hot",
      action: "game-account",
      items: sectionItems((product) => product.category === "game-account" || product.name.toLowerCase().includes("game"), 4),
    },
    {
      eyebrow: "Gaming setup",
      title: "Laptop và gear chiến game",
      action: "laptop",
      items: sectionItems((product) => product.category === "laptop" || product.category === "gaming", 4),
    },
    {
      eyebrow: "Best sellers",
      title: "Bán chạy trong cyber market",
      action: "all",
      items: [...products].sort((a, b) => b.sold - a.sold).slice(0, 4),
    },
  ];

  storefrontSections.innerHTML = sections
    .map(
      (section) => `
        <section class="store-section">
          <div class="section-head">
            <div>
              <p class="eyebrow">${section.eyebrow}</p>
              <h2>${section.title}</h2>
            </div>
            <button class="section-link" type="button" data-category-jump="${section.action}">Xem thêm</button>
          </div>
          <div class="feature-rail">
            ${section.items.map((product, index) => renderProductCard(product, index === 0 ? "spotlight-card" : "mini-card")).join("")}
          </div>
        </section>
      `,
    )
    .join("");
}

function cartEntries() {
  return Object.entries(state.cart)
    .map(([id, quantity]) => {
      const product = products.find((item) => item.id === id);
      return product ? { ...product, quantity } : null;
    })
    .filter(Boolean);
}

function totals() {
  const subtotal = cartEntries().reduce((sum, item) => sum + item.price * item.quantity, 0);
  const discount = subtotal >= 5000000 ? Math.round(subtotal * (state.dealPercent / 100)) : 0;
  const shipping = subtotal === 0 || subtotal >= 3000000 ? 0 : 35000;
  return { subtotal, discount, shipping, total: subtotal - discount + shipping };
}

function renderCart() {
  const entries = cartEntries();
  const quantity = entries.reduce((sum, item) => sum + item.quantity, 0);
  const summary = totals();

  cartCount.textContent = quantity;
  cartEmpty.hidden = entries.length > 0;

  cartItems.innerHTML = entries
    .map(
      (item) => `
        <article class="cart-item">
          <div>
            <h3>${item.name}</h3>
            <span>${formatCurrency(item.price)} x ${item.quantity}</span>
            <div class="qty">
              <button type="button" data-decrease="${item.id}" aria-label="Giảm ${item.name}">-</button>
              <strong>${item.quantity}</strong>
              <button type="button" data-increase="${item.id}" aria-label="Tăng ${item.name}">+</button>
            </div>
          </div>
          <button class="remove-btn" type="button" data-remove="${item.id}">Xóa</button>
        </article>
      `,
    )
    .join("");

  document.querySelector("#subtotal").textContent = formatCurrency(summary.subtotal);
  document.querySelector("#discount").textContent = `-${formatCurrency(summary.discount)}`;
  document.querySelector("#shipping").textContent = formatCurrency(summary.shipping);
  document.querySelector("#total").textContent = formatCurrency(summary.total);
  saveCart();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 1900);
}

function addToCart(id) {
  const product = products.find((item) => item.id === id);
  const current = state.cart[id] || 0;
  if (!product || current >= product.stock) {
    showToast("Sản phẩm đã đạt giới hạn tồn kho.");
    return;
  }

  state.cart[id] = current + 1;
  renderCart();
  showToast(`Đã thêm ${product.name}`);
}

function updateQuantity(id, nextQuantity) {
  const product = products.find((item) => item.id === id);
  if (!product) return;

  if (nextQuantity <= 0) {
    delete state.cart[id];
  } else {
    state.cart[id] = Math.min(nextQuantity, product.stock);
  }
  renderCart();
}

function openCart() {
  cartDrawer.classList.add("is-open");
  cartDrawer.setAttribute("aria-hidden", "false");
}

function closeCart() {
  cartDrawer.classList.remove("is-open");
  cartDrawer.setAttribute("aria-hidden", "true");
}

function tickDealTimer() {
  state.dealEndsIn = state.dealEndsIn > 0 ? state.dealEndsIn - 1 : 14 * 60 + 59;
  const minutes = String(Math.floor(state.dealEndsIn / 60)).padStart(2, "0");
  const seconds = String(state.dealEndsIn % 60).padStart(2, "0");
  dealTimer.textContent = `00:${minutes}:${seconds}`;
}

function pulseOnlineUsers() {
  const base = 247;
  const delta = Math.floor(Math.random() * 28);
  document.querySelector("#onlineUsers").textContent = base + delta;
}

async function hydrateAccountLink() {
  try {
    const response = await fetch("/api/me");
    const data = await response.json();
    if (data.user) {
      accountLink.textContent = data.user.name;
      accountLink.href = "/account";
      if (data.user.role === "admin") {
        accountLink.textContent = `${data.user.name} / Admin`;
      }
    }
  } catch {
    accountLink.textContent = "Đăng nhập";
    accountLink.href = "/login";
  }
}

async function loadProducts() {
  const response = await fetch("/api/products");
  if (!response.ok) throw new Error("Không tải được catalog sản phẩm.");
  const data = await response.json();
  products = data.products;
}

async function initStore() {
  renderProducts();
  try {
    await loadProducts();
  } catch (error) {
    productGrid.innerHTML = `<div class="empty-state">${error.message}</div>`;
    return;
  }
  renderProducts();
  renderStorefrontSections();
  renderCart();
  hydrateAccountLink();
  if (new URLSearchParams(window.location.search).has("openCart")) {
    openCart();
  }
}

document.addEventListener("click", (event) => {
  const addId = event.target.dataset.add;
  const increaseId = event.target.dataset.increase;
  const decreaseId = event.target.dataset.decrease;
  const removeId = event.target.dataset.remove;
  const categoryJump = event.target.dataset.categoryJump;
  const searchJump = event.target.dataset.searchJump;

  if (addId) addToCart(addId);
  if (increaseId) updateQuantity(increaseId, (state.cart[increaseId] || 0) + 1);
  if (decreaseId) updateQuantity(decreaseId, (state.cart[decreaseId] || 0) - 1);
  if (removeId) updateQuantity(removeId, 0);
  if (categoryJump) {
    categoryFilter.value = categoryJump;
    searchInput.value = "";
    priceRange.value = priceRange.max;
    renderProducts();
    document.querySelector("#products").scrollIntoView({ behavior: "smooth" });
  }
  if (searchJump) {
    searchInput.value = searchJump;
    categoryFilter.value = "all";
    priceRange.value = priceRange.max;
    renderProducts();
    document.querySelector("#products").scrollIntoView({ behavior: "smooth" });
  }
});

document.querySelector("#openCart").addEventListener("click", openCart);
document.querySelector("#closeCart").addEventListener("click", closeCart);
document.querySelector("#closeCartBtn").addEventListener("click", closeCart);
checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!cartEntries().length) {
    showToast("Giỏ hàng đang trống.");
    return;
  }

  const checkoutButton = document.querySelector("#checkoutBtn");
  const customer = Object.fromEntries(new FormData(checkoutForm).entries());
  const entries = cartEntries().map((item) => ({
    id: item.id,
    quantity: item.quantity,
  }));

  checkoutButton.disabled = true;
  checkoutButton.textContent = "Đang tạo đơn...";

  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer, items: entries }),
    });
    const data = await response.json();
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) throw new Error(data.error || "Không thể tạo đơn hàng.");

    state.cart = {};
    await loadProducts();
    renderCart();
    renderProducts();
    renderStorefrontSections();
    checkoutForm.reset();
    closeCart();
    showToast(`Đã tạo đơn #${data.orderId}, tổng ${formatCurrency(data.total)}.`);
  } catch (error) {
    showToast(error.message);
  } finally {
    checkoutButton.disabled = false;
    checkoutButton.textContent = "Đặt hàng thật vào database";
  }
});

document.querySelector("#randomDeal").addEventListener("click", () => {
  state.dealPercent = [10, 12, 15, 18, 20][Math.floor(Math.random() * 5)];
  dealPercent.textContent = `${state.dealPercent}%`;
  renderCart();
  showToast(`Deal mới đã bật: giảm ${state.dealPercent}%`);
});

[searchInput, categoryFilter, priceRange].forEach((control) => {
  control.addEventListener("input", renderProducts);
});

initStore();
tickDealTimer();
setInterval(tickDealTimer, 1000);
setInterval(pulseOnlineUsers, 2500);
