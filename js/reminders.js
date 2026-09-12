/* ============================================
   NOVA - Reminders JavaScript
   ============================================ */

var allReminders = [];
var currentFilter = "all";
var searchQuery = "";

document.addEventListener("DOMContentLoaded", function () {
  loadReminders();
  initFilters();
  initSearch();
  initNewReminder();
  initModalClose();
  if (window.lucide) lucide.createIcons();
});

async function loadReminders() {
  try {
    var result = await getReminders();
    allReminders = result.data || [];
    renderReminders();
  } catch (err) {
    console.error("Failed to load reminders:", err);
  }
}

function renderReminders() {
  var list = document.getElementById("remindersList");
  if (!list) return;

  var filtered = allReminders;

  if (currentFilter === "today") {
    filtered = filtered.filter(function (r) { return r.time.toLowerCase().indexOf("today") !== -1; });
  } else if (currentFilter === "upcoming") {
    filtered = filtered.filter(function (r) {
      return r.status === "pending" && r.time.toLowerCase().indexOf("today") === -1;
    });
  } else if (currentFilter === "completed") {
    filtered = filtered.filter(function (r) { return r.status === "completed"; });
  }

  if (searchQuery) {
    var q = searchQuery.toLowerCase();
    filtered = filtered.filter(function (r) { return r.title.toLowerCase().indexOf(q) !== -1; });
  }

  if (filtered.length === 0) {
    list.innerHTML = '<div class="empty-state"><div class="empty-icon">⏰</div><div class="empty-title">No reminders found</div><div class="empty-text">Create a new reminder or adjust your filters.</div></div>';
    return;
  }

  var html = "";
  filtered.forEach(function (r) {
    var badge = r.priority === "high" ? "badge-red" : (r.priority === "medium" ? "badge-amber" : "badge-cyan");
    var completedClass = r.status === "completed" ? " completed" : "";

    html += '<div class="reminder-card' + completedClass + '" data-id="' + r.id + '">';
    html += '<button type="button" class="reminder-check" data-action="toggle" aria-label="Toggle complete">✓</button>';
    html += '<div class="reminder-content">';
    html += '<div class="reminder-title">' + escapeHtml(r.title) + '</div>';
    html += '<div class="reminder-meta">';
    html += '<span class="reminder-time">' + escapeHtml(r.time) + '</span>';
    html += '<span class="badge ' + badge + '">' + r.priority + '</span>';
    html += '</div></div>';
    html += '<div class="reminder-actions">';
    html += '<button type="button" class="btn-icon-sm" data-action="edit" aria-label="Edit"><i data-lucide="pencil"></i></button>';
    html += '<button type="button" class="btn-icon-sm" data-action="delete" aria-label="Delete"><i data-lucide="trash-2"></i></button>';
    html += '</div></div>';
  });

  list.innerHTML = html;

  if (window.lucide) lucide.createIcons();

  list.querySelectorAll("[data-action]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var card = e.currentTarget.closest(".reminder-card");
      var id = Number(card.dataset.id);
      var action = e.currentTarget.dataset.action;
      if (action === "toggle") toggleReminder(id);
      else if (action === "delete") removeReminder(id);
      else if (action === "edit") editReminder(id);
    });
  });
}

async function toggleReminder(id) {
  var r = allReminders.filter(function (x) { return x.id === id; })[0];
  if (!r) return;
  var next = r.status === "completed" ? "pending" : "completed";
  r.status = next;
  renderReminders();
  try {
    await updateReminder(id, { status: next });
    showToast("success", next === "completed" ? "Completed!" : "Reopened", r.title);
  } catch (err) {
    r.status = next === "completed" ? "pending" : "completed";
    renderReminders();
  }
}

async function removeReminder(id) {
  var r = allReminders.filter(function (x) { return x.id === id; })[0];
  allReminders = allReminders.filter(function (x) { return x.id !== id; });
  renderReminders();
  try {
    await deleteReminder(id);
    showToast("info", "Reminder deleted", r ? r.title : "");
  } catch (err) {
    showToast("error", "Error", "Could not delete reminder.");
  }
}

function editReminder(id) {
  var r = allReminders.filter(function (x) { return x.id === id; })[0];
  if (!r) return;
  document.getElementById("reminderTitle").value = r.title;
  document.getElementById("reminderTime").value = r.time;
  document.getElementById("reminderPriority").value = r.priority;
  document.getElementById("reminderTitleError").classList.remove("show");
  document.getElementById("reminderTimeError").classList.remove("show");
  openModal("reminderModal");
  document.getElementById("saveReminderBtn").dataset.editId = id;
}

function initFilters() {
  var filters = document.getElementById("reminderFilters");
  if (!filters) return;
  filters.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      filters.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
      tab.classList.add("active");
      currentFilter = tab.dataset.filter;
      renderReminders();
    });
  });
}

function initSearch() {
  var search = document.getElementById("reminderSearch");
  if (!search) return;
  search.addEventListener("input", function () {
    searchQuery = search.value.trim();
    renderReminders();
  });
}

function initNewReminder() {
  var btn = document.getElementById("newReminderBtn");
  var saveBtn = document.getElementById("saveReminderBtn");
  if (!btn || !saveBtn) return;

  btn.addEventListener("click", function () {
    document.getElementById("reminderTitle").value = "";
    document.getElementById("reminderTime").value = "";
    document.getElementById("reminderPriority").value = "medium";
    document.getElementById("reminderTitleError").classList.remove("show");
    document.getElementById("reminderTimeError").classList.remove("show");
    delete saveBtn.dataset.editId;
    openModal("reminderModal");
  });

  saveBtn.addEventListener("click", async function () {
    var title = document.getElementById("reminderTitle").value.trim();
    var time = document.getElementById("reminderTime").value.trim();
    var priority = document.getElementById("reminderPriority").value;

    var bad = false;
    if (!title) { document.getElementById("reminderTitleError").classList.add("show"); bad = true; }
    if (!time) { document.getElementById("reminderTimeError").classList.add("show"); bad = true; }
    if (bad) return;

    var editId = saveBtn.dataset.editId;

    try {
      if (editId) {
        await updateReminder(Number(editId), { title: title, time: time, priority: priority });
        var r = allReminders.filter(function (x) { return x.id === Number(editId); })[0];
        if (r) { r.title = title; r.time = time; r.priority = priority; }
        showToast("success", "Reminder updated", title);
      } else {
        var result = await createReminder({ title: title, time: time, priority: priority });
        allReminders.unshift(result.data);
        showToast("success", "Reminder created", title);
      }
      closeModal("reminderModal");
      delete saveBtn.dataset.editId;
      renderReminders();
    } catch (err) {
      showToast("error", "Error", "Could not save reminder.");
    }
  });
}

function initModalClose() {
  document.addEventListener("click", function (e) {
    if (e.target.hasAttribute("data-close-modal")) {
      var modal = e.target.closest(".modal-overlay");
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
    }
  });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}