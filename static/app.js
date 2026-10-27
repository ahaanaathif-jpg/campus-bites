const CART_KEY = "campus-bites-cart";

function readCart() {
  try {
    const value = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
    return Array.isArray(value) ? value.filter(item => Number.isInteger(item.food_id) && Number.isFinite(item.price) && Number.isInteger(item.quantity)) : [];
  } catch {
    return [];
  }
}

function writeCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartCount();
}

function updateCartCount() {
  const count = readCart().reduce((sum, item) => sum + item.quantity, 0);
  document.querySelectorAll("#cart-count").forEach(element => { element.textContent = count; });
}

function money(amount) {
  return `₹${Math.round(amount)}`;
}

function addItem(foodId, name, price) {
  const cart = readCart();
  const existing = cart.find(item => item.food_id === foodId);
  if (existing) existing.quantity = Math.min(20, existing.quantity + 1);
  else cart.push({ food_id: foodId, name, price, quantity: 1 });
  writeCart(cart);
}

function renderCart() {
  const container = document.getElementById("cart-items");
  if (!container) return;
  const cart = readCart();
  const empty = document.getElementById("cart-empty");
  const summary = document.querySelector(".order-summary");
  empty.hidden = cart.length !== 0;
  summary.hidden = cart.length === 0;
  container.replaceChildren();
  cart.forEach(item => {
    const row = document.createElement("article");
    row.className = "cart-row";
    const details = document.createElement("div");
    details.className = "cart-row-details";
    const title = document.createElement("h2");
    title.textContent = item.name;
    const price = document.createElement("span");
    price.textContent = `${money(item.price)} each`;
    details.append(title, price);
    const controls = document.createElement("div");
    controls.className = "quantity-controls";
    controls.innerHTML = `<button type="button" aria-label="Decrease ${escapeHtml(item.name)} quantity" data-quantity="-1">−</button><span>${item.quantity}</span><button type="button" aria-label="Increase ${escapeHtml(item.name)} quantity" data-quantity="1">+</button>`;
    controls.addEventListener("click", event => {
      const button = event.target.closest("button[data-quantity]");
      if (!button) return;
      const next = readCart();
      const selected = next.find(entry => entry.food_id === item.food_id);
      selected.quantity += Number(button.dataset.quantity);
      if (selected.quantity <= 0) writeCart(next.filter(entry => entry.food_id !== item.food_id));
      else if (selected.quantity <= 20) writeCart(next);
      renderCart();
    });
    const lineTotal = document.createElement("strong");
    lineTotal.textContent = money(item.price * item.quantity);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-item";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => { writeCart(readCart().filter(entry => entry.food_id !== item.food_id)); renderCart(); });
    row.append(details, controls, lineTotal, remove);
    container.append(row);
  });
  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const subtotal = document.getElementById("cart-subtotal");
  const totalElement = document.getElementById("cart-total");
  if (subtotal) subtotal.textContent = money(total);
  if (totalElement) totalElement.textContent = money(total);
  const checkoutLink = document.getElementById("checkout-link");
  if (checkoutLink && !cart.length) checkoutLink.setAttribute("aria-disabled", "true");
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

function renderCheckout() {
  const container = document.getElementById("checkout-items");
  if (!container) return;
  const cart = readCart();
  if (!cart.length) {
    window.location.replace("/cart");
    return;
  }
  container.replaceChildren();
  cart.forEach(item => {
    const row = document.createElement("div");
    row.className = "checkout-item";
    const name = document.createElement("span");
    name.textContent = `${item.quantity} × ${item.name}`;
    const amount = document.createElement("strong");
    amount.textContent = money(item.price * item.quantity);
    row.append(name, amount);
    container.append(row);
  });
  document.getElementById("checkout-total").textContent = money(cart.reduce((sum, item) => sum + item.price * item.quantity, 0));
}

function wireCheckout() {
  const form = document.getElementById("checkout-form");
  if (!form) return;
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const errorBox = document.getElementById("checkout-errors");
    errorBox.hidden = true;
    if (!form.reportValidity()) return;
    const button = document.querySelector("button[form='checkout-form']");
    button.disabled = true;
    button.textContent = "Placing your order…";
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    payload.items = readCart().map(item => ({ food_id: item.food_id, quantity: item.quantity }));
    try {
      const response = await fetch("/api/orders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok) throw new Error((result.errors || ["Something went wrong."]).join(" "));
      localStorage.removeItem(CART_KEY);
      window.location.assign(result.redirect);
    } catch (error) {
      errorBox.textContent = error.message || "We couldn't place that order. Please try again.";
      errorBox.hidden = false;
      button.disabled = false;
      button.innerHTML = 'Place my order <span>→</span>';
    }
  });
}

function wireMenu() {
  const grid = document.getElementById("food-grid");
  if (!grid) return;
  document.querySelectorAll("[data-add]").forEach(button => button.addEventListener("click", () => {
    addItem(Number(button.dataset.add), button.dataset.name, Number(button.dataset.price));
    const original = button.innerHTML;
    button.innerHTML = '<span>✓</span> Added';
    button.classList.add("added");
    window.setTimeout(() => { button.innerHTML = original; button.classList.remove("added"); }, 900);
  }));
  let selectedCategory = "all";
  const search = document.getElementById("menu-search");
  const filter = () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    grid.querySelectorAll(".food-card").forEach(card => {
      const matches = (selectedCategory === "all" || card.dataset.category === selectedCategory) && card.dataset.name.includes(query);
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    document.getElementById("menu-empty").hidden = visible !== 0;
  };
  document.querySelectorAll(".category-tab").forEach(button => button.addEventListener("click", () => {
    selectedCategory = button.dataset.category;
    document.querySelectorAll(".category-tab").forEach(tab => tab.classList.toggle("selected", tab === button));
    filter();
  }));
  search.addEventListener("input", filter);
}

document.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  wireMenu();
  renderCart();
  renderCheckout();
  wireCheckout();
});
