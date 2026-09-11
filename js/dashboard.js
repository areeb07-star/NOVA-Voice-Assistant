/* ============================================
   NOVA - Dashboard JavaScript (SAFE VERSION)
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
  console.log("[NOVA Dashboard] init");
  initGreeting();
  loadDashboardStats();
  loadChatHistory();
  initAssistantInput();
  initMicButton();
  initQuickActions();
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
    const result = await getDashboardStats();
    const stats = result.data;

    const cards = [
      { icon: "⏰", value: stats.remindersToday, label: "Today's Reminders" },
      { icon: "📝", value: stats.notesCount, label: "Notes" },
      { icon: "🛒", value: stats.shoppingItems, label: "Shopping Items" },
      { icon: "📚", value: stats.studyTasks, label: "Study Tasks" },
      { icon: "🎯", value: stats.goalProgress + "%", label: "Goal Progress" }
    ];

    grid.innerHTML = cards.map(function (card) {
      return '' +
        '<div class="stat-card">' +
          '<div class="stat-icon">' + card.icon + '</div>' +
          '<div class="stat-value">' + card.value + '</div>' +
          '<div class="stat-label">' + card.label + '</div>' +
        '</div>';
    }).join("");
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

/* ---------- Chat ---------- */
async function loadChatHistory() {
  const container = document.getElementById("chatContainer");
  if (!container) return;

  try {
    const result = await getChatHistory();
    result.data.forEach(function (msg) {
      container.appendChild(createChatMessage(msg.sender, msg.text, msg.time));
    });
    scrollChatToBottom();
  } catch (err) {
    console.error("Failed to load chat:", err);
  }
}

function createChatMessage(sender, text, time) {
  const msg = document.createElement("div");
  msg.className = "chat-message " + sender;

  const name = getUserName();
  const avatarText = sender === "nova" ? "N" : (name.charAt(0) || "U").toUpperCase();
  const senderName = sender === "nova" ? "NOVA" : "YOU";

  const safeText = escapeHtml(text).split("\n").join("<br>");

  msg.innerHTML =
    '<div class="chat-avatar">' + avatarText + '</div>' +
    '<div>' +
      '<div class="chat-sender">' + senderName + '</div>' +
      '<div class="chat-bubble">' + safeText + '</div>' +
      '<div class="chat-time">' + time + '</div>' +
    '</div>';

  return msg;
}

function showTypingIndicator() {
  const container = document.getElementById("chatContainer");
  if (!container) return;

  const typing = document.createElement("div");
  typing.className = "chat-message nova chat-typing";
  typing.id = "typingIndicator";

  typing.innerHTML =
    '<div class="chat-avatar">N</div>' +
    '<div>' +
      '<div class="chat-sender">NOVA</div>' +
      '<div class="chat-bubble">' +
        '<div class="typing-dots">' +
          '<span></span><span></span><span></span>' +
        '</div>' +
      '</div>' +
    '</div>';

  container.appendChild(typing);
  scrollChatToBottom();
}

function removeTypingIndicator() {
  const typing = document.getElementById("typingIndicator");
  if (typing) typing.remove();
}

function scrollChatToBottom() {
  const container = document.getElementById("chatContainer");
  if (container) container.scrollTop = container.scrollHeight;
}

/* ---------- Assistant Input ---------- */
function initAssistantInput() {
  const input = document.getElementById("assistantInput");
  const sendBtn = document.getElementById("assistantSend");
  if (!input || !sendBtn) return;

  console.log("[NOVA Dashboard] chat ready");

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    input.value = "";

    const container = document.getElementById("chatContainer");
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    container.appendChild(createChatMessage("user", text, now));
    scrollChatToBottom();

    if (window.NOVA_VOICE) window.NOVA_VOICE.updateVoiceStatus("thinking");
    showTypingIndicator();

    try {
      const result = await sendAssistantMessage(text);
      removeTypingIndicator();

      const novaMsg = result.data;
      container.appendChild(createChatMessage("nova", novaMsg.text, novaMsg.time));
      scrollChatToBottom();

      if (window.NOVA_VOICE) {
        window.NOVA_VOICE.updateVoiceStatus("speaking");
        setTimeout(function () {
          window.NOVA_VOICE.updateVoiceStatus("idle");
        }, 1500);
      }
    } catch (err) {
      removeTypingIndicator();
      showToast("error", "Error", "Failed to get response from NOVA.");
    }
  }

  sendBtn.addEventListener("click", function (e) {
    e.preventDefault();
    sendMessage();
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
}

/* ---------- Mic ---------- */
function initMicButton() {
  const micBtn = document.getElementById("micBtn");
  if (!micBtn) return;

  micBtn.addEventListener("click", function (e) {
    e.preventDefault();
    if (window.NOVA_VOICE) window.NOVA_VOICE.toggleMicrophone();
  });
}

/* ---------- Quick Actions ---------- */
function initQuickActions() {
  document.querySelectorAll(".quick-action").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const input = document.getElementById("assistantInput");
      if (input) {
        input.value = btn.dataset.quick;
        input.focus();
      }
    });
  });
}

/* ---------- Escape HTML ---------- */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}