/* ============================================
   NOVA - Main JavaScript (FIXED)
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  initMobileMenu();
  initNotifications();
  initSmoothScroll();
  initPageTransitions();
  initLogout();
  initCurrentPage();
  initModalOverlayClose();
  initEscapeKey();
});

/* ---------- Sidebar ---------- */
function initSidebar() {
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main-content");
  const collapseBtn = document.querySelector("[data-sidebar-collapse]");

  if (!sidebar) return;

  const isCollapsed = localStorage.getItem("nova-sidebar-collapsed") === "true";
  if (isCollapsed && window.innerWidth > 1024) {
    sidebar.classList.add("collapsed");
    if (mainContent) mainContent.classList.add("sidebar-collapsed");
  }

  if (collapseBtn) {
    collapseBtn.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");
      if (mainContent) mainContent.classList.toggle("sidebar-collapsed");
      localStorage.setItem(
        "nova-sidebar-collapsed",
        sidebar.classList.contains("collapsed")
      );
    });
  }
}

/* ---------- Mobile Menu ---------- */
function initMobileMenu() {
  const hamburger = document.querySelector(".hamburger");
  const sidebar = document.querySelector(".sidebar");

  if (!hamburger || !sidebar) return;

  let overlay = document.querySelector(".sidebar-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "sidebar-overlay";
    document.body.appendChild(overlay);
  }

  hamburger.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    sidebar.classList.toggle("mobile-open");
    overlay.classList.toggle("active");
  });

  overlay.addEventListener("click", () => {
    sidebar.classList.remove("mobile-open");
    overlay.classList.remove("active");
  });

  sidebar.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      if (window.innerWidth <= 1024) {
        sidebar.classList.remove("mobile-open");
        overlay.classList.remove("active");
      }
    });
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 1024) {
      sidebar.classList.remove("mobile-open");
      overlay.classList.remove("active");
    }
  });
}

/* ---------- Notifications ---------- */
function initNotifications() {
  const notifBtn = document.querySelector("[data-notifications]");
  if (!notifBtn) return;

  notifBtn.addEventListener("click", (e) => {
    e.preventDefault();
    showToast("info", "🔔 Notifications", "You have 3 new notifications.");
  });
}

/* ---------- Smooth Scroll ---------- */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", (e) => {
      const href = anchor.getAttribute("href");
      if (!href || href === "#") return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
}

/* ---------- Page Transitions ---------- */
function initPageTransitions() {
  document.body.classList.add("page-enter");
}

/* ---------- Logout ---------- */
function initLogout() {
  const logoutBtn = document.getElementById("logoutBtn");
  if (!logoutBtn) return;

  logoutBtn.addEventListener("click", (e) => {
    e.preventDefault();
    localStorage.removeItem("nova-auth-token");
    localStorage.removeItem("nova-user-name");
    showToast("info", "Logged out", "See you soon!");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 600);
  });
}

/* ---------- Active Nav Highlight ---------- */
function initCurrentPage() {
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-item").forEach((item) => {
    const href = item.getAttribute("href");
    if (href === currentPage) {
      item.classList.add("active");
    }
  });
}

/* ---------- Toast Notifications ---------- */
function showToast(type, title, message, duration = 4000) {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const icons = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || "ℹ️"}</span>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-message">${message}</div>` : ""}
    </div>
    <button class="toast-close" aria-label="Close notification">✕</button>
  `;

  container.appendChild(toast);

  const removeToast = () => {
    toast.classList.add("removing");
    setTimeout(() => toast.remove(), 300);
  };

  toast.querySelector(".toast-close").addEventListener("click", removeToast);
  setTimeout(removeToast, duration);
}

/* ---------- Modal Helpers ---------- */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

/* Click outside modal → close */
function initModalOverlayClose() {
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-overlay")) {
      e.target.classList.remove("active");
      document.body.style.overflow = "";
    }
  });
}

/* Escape key → close all modals */
function initEscapeKey() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.active").forEach((modal) => {
        modal.classList.remove("active");
      });
      document.body.style.overflow = "";
    }
  });
}

/* ---------- Format Helpers ---------- */
function formatCurrency(amount) {
  return "₹" + Number(amount).toLocaleString("en-IN");
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function getUserName() {
  return localStorage.getItem("nova-user-name") || "User";
}

function setUserName(name) {
  localStorage.setItem("nova-user-name", name);
}

/* ---------- Expose Globals ---------- */
window.NOVA = {
  showToast,
  openModal,
  closeModal,
  formatCurrency,
  formatDate,
  getGreeting,
  getUserName,
  setUserName
};