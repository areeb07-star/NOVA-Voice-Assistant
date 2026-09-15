/* ============================================
   NOVA - Expenses JavaScript
   ============================================ */

let allExpenses = [];

const CATEGORY_ICONS = {
  Food: "🍔",
  Travel: "🚌",
  Education: "📚",
  Shopping: "🛍️",
  Bills: "📄",
  Other: "📦"
};

document.addEventListener("DOMContentLoaded", () => {
  loadExpenses();
  initAddExpense();
});

async function loadExpenses() {
  try {
    const result = await getExpenses();
    allExpenses = result.data;
    renderExpenses();
  } catch (err) {
    console.error("Failed to load expenses:", err);
  }
}

function renderExpenses() {
  renderSummary();
  renderCategories();
  renderExpenseList();
}

function renderSummary() {
  const total = allExpenses.reduce((sum, e) => sum + e.amount, 0);
  const now = new Date();
  const monthStr = now.toISOString().slice(0, 7);
  const todayStr = now.toISOString().split("T")[0];

  const monthTotal = allExpenses
    .filter((e) => e.date.startsWith(monthStr))
    .reduce((sum, e) => sum + e.amount, 0);

  const todayTotal = allExpenses
    .filter((e) => e.date === todayStr)
    .reduce((sum, e) => sum + e.amount, 0);

  document.getElementById("totalSpent").textContent = formatCurrency(total);
  document.getElementById("monthSpent").textContent = formatCurrency(monthTotal);
  document.getElementById("todaySpent").textContent = formatCurrency(todayTotal);
}

function renderCategories() {
  const container = document.getElementById("expenseCategories");
  if (!container) return;

  const categories = ["Food", "Travel", "Education", "Shopping", "Bills", "Other"];

  container.innerHTML = categories.map((cat) => {
    const amount = allExpenses
      .filter((e) => e.category === cat)
      .reduce((sum, e) => sum + e.amount, 0);

    return `
      <div class="expense-category-card">
        <div class="expense-category-icon">${CATEGORY_ICONS[cat]}</div>
        <div class="expense-category-name">${cat}</div>
        <div class="expense-category-amount">${formatCurrency(amount)}</div>
      </div>
    `;
  }).join("");
}

function renderExpenseList() {
  const list = document.getElementById("expenseList");
  if (!list) return;

  if (allExpenses.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">💰</div>
        <div class="empty-title">No expenses yet</div>
        <div class="empty-text">Add your first expense to start tracking.</div>
      </div>
    `;
    return;
  }

  const sorted = [...allExpenses].sort((a, b) => new Date(b.date) - new Date(a.date));

  list.innerHTML = sorted.map((e) => `
    <div class="expense-item" data-id="${e.id}">
      <div class="expense-item-icon">${CATEGORY_ICONS[e.category] || "📦"}</div>
      <div class="expense-item-content">
        <div class="expense-item-title">${e.title}</div>
        <div class="expense-item-meta">${e.category} · ${formatDate(e.date)}</div>
      </div>
      <div class="expense-item-amount">${formatCurrency(e.amount)}</div>
      <div class="expense-item-actions">
        <button class="btn-icon-sm btn-ghost" data-action="delete" aria-label="Delete">🗑</button>
      </div>
    </div>
  `).join("");

  list.querySelectorAll("[data-action='delete']").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const item = e.target.closest(".expense-item");
      const id = Number(item.dataset.id);
      await deleteExpense(id);
      allExpenses = allExpenses.filter((x) => x.id !== id);
      renderExpenses();
      showToast("info", "Expense deleted", "The expense has been removed.");
    });
  });
}

function initAddExpense() {
  const btn = document.getElementById("addExpenseBtn");
  const saveBtn = document.getElementById("saveExpenseBtn");
  if (!btn || !saveBtn) return;

  btn.addEventListener("click", () => {
    document.getElementById("expenseTitle").value = "";
    document.getElementById("expenseAmount").value = "";
    document.getElementById("expenseCategory").value = "Other";
    openModal("expenseModal");
  });

  saveBtn.addEventListener("click", async () => {
    const title = document.getElementById("expenseTitle").value.trim();
    const amount = Number(document.getElementById("expenseAmount").value);
    const category = document.getElementById("expenseCategory").value;

    let valid = true;
    if (!title) { document.getElementById("expenseTitleError").classList.add("show"); valid = false; }
    if (!amount || amount <= 0) { document.getElementById("expenseAmountError").classList.add("show"); valid = false; }
    if (!valid) return;

    const result = await createExpense({ title, amount, category });
    allExpenses.unshift(result.data);
    closeModal("expenseModal");
    renderExpenses();
    showToast("success", "Expense added", title + " — " + formatCurrency(amount));
  });
}

document.addEventListener("click", (e) => {
  if (e.target.hasAttribute("data-close-modal")) {
    const modal = e.target.closest(".modal-overlay");
    if (modal) modal.classList.remove("active");
    document.body.style.overflow = "";
  }
});