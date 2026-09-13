/* ============================================
   NOVA - Dashboard JavaScript (Person 4)
   - Delegates chat/mic/quick-actions to voice.js
   - Only handles: greeting, stats, notifications
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
  console.log("[NOVA Dashboard] init");
  initGreeting();
  loadDashboardStats();
  initNotifications();
  updateUserName();
});

/* ---------- Greeting ---------- */
function initGreeting() {
  const greetingTitle = document.getElementById("greetingTitle");
  if (!greetingTitle) return;
  const name = getUserName();
  greetingTitle.textContent = getGreeting() + ", " + name + " 👋";
}

function updateUserName() {
  const name = getUserName();
  const sidebarName = document.getElementById("sidebarUserName");
  if (sidebarName) sidebarName.textContent = name;
}

/* ---------- Stats ---------- */
async function loadDashboardStats() {
  const grid = document.getElementById("dashboardGrid");
  if (!grid) return;

  try {
    // If Person 1's api.js exists, use it. Otherwise, use static values.
    if (typeof getDashboardStats === 'function') {
      const result = await getDashboardStats();
      const stats = result.data;
      renderStats(grid, stats);
    } else {
      // Static fallback
      renderStats(grid, {
        remindersToday: 0,
        notesCount: 0,
        shoppingItems: 0,
        studyTasks: 0,
        goalProgress: 0
      });
    }
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

function renderStats(grid, stats) {
  const cards = [
    { icon: "clock", value: stats.remindersToday || 0, label: "Today's Reminders" },
    { icon: "file-text", value: stats.notesCount || 0, label: "Notes" },
    { icon: "shopping-cart", value: stats.shoppingItems || 0, label: "Shopping Items" },
    { icon: "book-open", value: stats.studyTasks || 0, label: "Study Tasks" },
    { icon: "target", value: (stats.goalProgress || 0) + "%", label: "Goal Progress" }
  ];

  grid.innerHTML = cards.map(function (card) {
    return '<div class="stat-card">' +
      '<div class="stat-icon"><i data-lucide="' + card.icon + '"></i></div>' +
      '<div class="stat-value">' + card.value + '</div>' +
      '<div class="stat-label">' + card.label + '</div>' +
    '</div>';
  }).join("");

  if (window.lucide) lucide.createIcons();
}

/* ---------- Notifications ---------- */
function initNotifications() {
  const notifBtn = document.getElementById("notifBtn");
  if (!notifBtn) return;
  notifBtn.addEventListener("click", function () {
    if (window.NOVA && window.NOVA.showToast) {
      window.NOVA.showToast("info", "🔔 Notifications", "You have no new notifications.");
    }
  });
}

/* ---------- Helpers ---------- */
function getGreeting() {
  var h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function getUserName() {
  return localStorage.getItem("nova-user-name") || "User";
}