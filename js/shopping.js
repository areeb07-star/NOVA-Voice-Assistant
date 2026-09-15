/* ============================================
   NOVA - Shopping JavaScript (FIXED)
   ============================================ */

let allShopping = [];
let searchQuery = "";

document.addEventListener("DOMContentLoaded", () => {
  loadShopping();
  initSearch();
  initAddItem();
  initModalClose();
});

/* ---------- Load ---------- */
async function loadShopping() {
  try {
    const result = await getShoppingItems();
    allShopping = result.data || [];
    renderShopping();
  } catch (err) {
    console.error("Failed to load shopping items:", err);
    showToast("error", "Error", "Could not load shopping list.");
  }
}

/* ---------- Render ---------- */
function renderShopping() {
  const list = document.getElementById("shoppingList");
  if (!list) return;

  // Apply search filter
  let filtered = allShopping;
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter((i) => i.name.toLowerCase().includes(q));
  }

  // Update progress bar
  const total = allShopping.length;
  const completed = allShopping.filter((i) => i.purchased).length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  const progressText = document.getElementById("shoppingProgressText");
  const progressBar = document.getElementById("shoppingProgressBar");
  if (progressText) progressText.textContent = `${completed} of ${total} items completed`;
  if (progressBar) progressBar.style.width = percent + "%";

  // Empty state
  if (filtered.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🛒</div>
        <div class="empty-title">No items found</div>
        <div class="empty-text">Add a new item or adjust your search.</div>
      </div>
    `;
    return;
  }

  // Render items
  list.innerHTML = filtered.map((i) => `
    <div class="shopping-item ${i.purchased ? "purchased" : ""}" data-id="${i.id}">
      <button type="button" class="shopping-check" data-action="toggle" aria-label="Toggle purchased">✓</button>
      <div class="shopping-content">
        <span class="shopping-name">${escapeHtml(i.name)}</span>
        <span class="shopping-qty">×${i.quantity}</span>
        <span class="badge badge-violet">${escapeHtml(i.category)}</span>
      </div>
      <div class="shopping-actions">
        <button type="button" class="btn-icon-sm btn-ghost" data-action="edit" aria-label="Edit">✎</button>
        <button type="button" class="btn-icon-sm btn-ghost" data-action="delete" aria-label="Delete">🗑</button>
      </div>
    </div>
  `).join("");

  // Attach ONE delegated listener (not per-button)
  list.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", handleItemAction);
  });
}

/* ---------- Single delegated handler ---------- */
function handleItemAction(e) {
  e.preventDefault();
  e.stopPropagation();

  const btn = e.currentTarget;
  const item = btn.closest(".shopping-item");
  if (!item) return;

  const id = Number(item.dataset.id);
  const action = btn.dataset.action;

  if (action === "toggle") togglePurchased(id);
  else if (action === "edit") editShoppingItem(id);
  else if (action === "delete") removeShoppingItem(id);
}

/* ---------- Actions ---------- */
async function togglePurchased(id) {
  const item = allShopping.find((i) => i.id === id);
  if (!item) return;

  item.purchased = !item.purchased;

  // Optimistic UI update
  renderShopping();

  try {
    await updateShoppingItem(id, { purchased: item.purchased });
  } catch (err) {
    // Rollback on failure
    item.purchased = !item.purchased;
    renderShopping();
    showToast("error", "Error", "Could not update item.");
  }
}

async function removeShoppingItem(id) {
  const item = allShopping.find((i) => i.id === id);
  if (!item) return;

  allShopping = allShopping.filter((i) => i.id !== id);
  renderShopping();

  try {
    await deleteShoppingItem(id);
    showToast("info", "Item removed", item.name);
  } catch (err) {
    showToast("error", "Error", "Could not delete item.");
  }
}

function editShoppingItem(id) {
  const item = allShopping.find((i) => i.id === id);
  if (!item) return;

  document.getElementById("shoppingName").value = item.name;
  document.getElementById("shoppingQty").value = item.quantity;
  document.getElementById("shoppingCategory").value = item.category;
  document.getElementById("shoppingNameError").classList.remove("show");

  openModal("shoppingModal");
  document.getElementById("saveShoppingBtn").dataset.editId = id;
}

/* ---------- Search ---------- */
function initSearch() {
  const search = document.getElementById("shoppingSearch");
  if (!search) return;

  search.addEventListener("input", () => {
    searchQuery = search.value.trim();
    renderShopping();
  });
}

/* ---------- Add / Save ---------- */
function initAddItem() {
  const btn = document.getElementById("addShoppingBtn");
  const saveBtn = document.getElementById("saveShoppingBtn");
  if (!btn || !saveBtn) return;

  btn.addEventListener("click", () => {
    document.getElementById("shoppingName").value = "";
    document.getElementById("shoppingQty").value = "1";
    document.getElementById("shoppingCategory").value = "Other";
    document.getElementById("shoppingNameError").classList.remove("show");
    delete saveBtn.dataset.editId;
    openModal("shoppingModal");
  });

  saveBtn.addEventListener("click", async () => {
    const name = document.getElementById("shoppingName").value.trim();
    const quantity = Math.max(1, Number(document.getElementById("shoppingQty").value) || 1);
    const category = document.getElementById("shoppingCategory").value;

    // Validate
    if (!name) {
      document.getElementById("shoppingNameError").classList.add("show");
      return;
    }

    const editId = saveBtn.dataset.editId;

    try {
      if (editId) {
        // Update existing
        await updateShoppingItem(Number(editId), { name, quantity, category });
        const item = allShopping.find((i) => i.id === Number(editId));
        if (item) {
          item.name = name;
          item.quantity = quantity;
          item.category = category;
        }
        showToast("success", "Item updated", name);
      } else {
        // Create new
        const result = await createShoppingItem({ name, quantity, category });
        allShopping.unshift(result.data);
        showToast("success", "Item added", name);
      }

      closeModal("shoppingModal");
      delete saveBtn.dataset.editId;
      renderShopping();
    } catch (err) {
      console.error(err);
      showToast("error", "Error", "Could not save item.");
    }
  });
}

/* ---------- Modal Close (once, here — NOT in main.js) ---------- */
function initModalClose() {
  document.addEventListener("click", (e) => {
    if (e.target.hasAttribute("data-close-modal")) {
      const modal = e.target.closest(".modal-overlay");
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
    }
  });
}

/* ---------- HTML Escape (safety) ---------- */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}