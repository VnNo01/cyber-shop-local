const tabs = document.querySelectorAll("[data-tab]");
const forms = {
  login: document.querySelector("#loginForm"),
  register: document.querySelector("#registerForm"),
};
const statusBox = document.querySelector("#authStatus");

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.style.color = isError ? "var(--pink)" : "var(--lime)";
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function submitAuth(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Có lỗi xảy ra.");
  return data;
}

tabs.forEach((button) => {
  button.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.toggle("is-active", item === button));
    Object.entries(forms).forEach(([key, form]) => {
      form.classList.toggle("is-active", key === button.dataset.tab);
    });
    setStatus("");
  });
});

forms.login.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Đang đăng nhập...");
  try {
    await submitAuth("/api/login", formPayload(forms.login));
    window.location.href = "/account";
  } catch (error) {
    setStatus(error.message, true);
  }
});

forms.register.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Đang tạo tài khoản...");
  try {
    await submitAuth("/api/register", formPayload(forms.register));
    window.location.href = "/account";
  } catch (error) {
    setStatus(error.message, true);
  }
});

const params = new URLSearchParams(window.location.search);
if (params.has("oauth_error")) {
  setStatus("OAuth chưa hoàn tất. Kiểm tra cấu hình provider hoặc thử lại.", true);
}
