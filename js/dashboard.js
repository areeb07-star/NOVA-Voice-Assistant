/* ============================================
   NOVA - Dashboard JavaScript (with Summarize + Device Action)
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
  initGreeting();
  loadDashboardStats();
  loadChatHistory();
  initAssistantInput();
  initMicButton();
  initQuickActions();
  updateUserName();
  initSummarizeFile();
  initDeviceActionHandler();

  if (window.lucide) lucide.createIcons();
});

/* ---------- Greeting ---------- */
function initGreeting() {
  const el = document.getElementById("greetingTitle");
  if (!el) return;
  el.textContent = getGreeting() + ", " + getUserName() + " 👋";
}

function updateUserName() {
  const name = getUserName();
  const side = document.getElementById("sidebarUserName");
  if (side) side.textContent = name;
}

/* ---------- Stats ---------- */
async function loadDashboardStats() {
  const grid = document.getElementById("dashboardGrid");
  if (!grid) return;
  try {
    const result = await getDashboardStats();
    const s = result.data;
    const cards = [
      { icon: "clock",       value: s.remindersToday,    label: "Today's Reminders" },
      { icon: "file-text",   value: s.notesCount,        label: "Notes" },
      { icon: "shopping-cart", value: s.shoppingItems,   label: "Shopping Items" },
      { icon: "book-open",   value: s.studyTasks,        label: "Study Tasks" },
      { icon: "target",      value: s.goalProgress + "%", label: "Goal Progress" }
    ];
    grid.innerHTML = cards.map(c =>
      '<div class="stat-card">' +
        '<div class="stat-icon"><i data-lucide="' + c.icon + '"></i></div>' +
        '<div class="stat-value">' + c.value + '</div>' +
        '<div class="stat-label">' + c.label + '</div>' +
      '</div>'
    ).join("");
    if (window.lucide) lucide.createIcons();
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
    result.data.forEach(msg => {
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
  const t = document.createElement("div");
  t.className = "chat-message nova chat-typing";
  t.id = "typingIndicator";
  t.innerHTML =
    '<div class="chat-avatar">N</div>' +
    '<div>' +
      '<div class="chat-sender">NOVA</div>' +
      '<div class="chat-bubble">' +
        '<div class="typing-dots"><span></span><span></span><span></span></div>' +
      '</div>' +
    '</div>';
  container.appendChild(t);
  scrollChatToBottom();
}

function removeTypingIndicator() {
  const t = document.getElementById("typingIndicator");
  if (t) t.remove();
}

function scrollChatToBottom() {
  const c = document.getElementById("chatContainer");
  if (c) c.scrollTop = c.scrollHeight;
}

/* ---------- Assistant Input ---------- */
function initAssistantInput() {
  const input = document.getElementById("assistantInput");
  const sendBtn = document.getElementById("assistantSend");
  if (!input || !sendBtn) return;

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

      if (novaMsg.device_action) {
        handleDeviceAction(novaMsg.device_action);
      }

      if (window.NOVA_VOICE) {
        window.NOVA_VOICE.updateVoiceStatus("speaking");
        setTimeout(() => window.NOVA_VOICE.updateVoiceStatus("idle"), 1500);
      }
    } catch (err) {
      removeTypingIndicator();
      showToast("error", "Error", "Failed to get response from NOVA.");
    }
  }

  sendBtn.addEventListener("click", e => { e.preventDefault(); sendMessage(); });
  input.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); sendMessage(); }
  });
}

/* ---------- Mic ---------- */
function initMicButton() {
  const mic = document.getElementById("micBtn");
  if (!mic) return;
  mic.addEventListener("click", e => {
    e.preventDefault();
    if (window.NOVA_VOICE) window.NOVA_VOICE.toggleMicrophone();
  });
}

/* ---------- Quick Actions ---------- */
function initQuickActions() {
  document.querySelectorAll(".quick-action").forEach(btn => {
    btn.addEventListener("click", e => {
      e.preventDefault();
      if (btn.id === "summarizeFileBtn") return; // handled elsewhere
      const input = document.getElementById("assistantInput");
      if (input) { input.value = btn.dataset.quick; input.focus(); }
    });
  });
}

/* ---------- Summarize File ---------- */
function initSummarizeFile() {
  const chip = document.getElementById("summarizeFileBtn");
  const attach = document.getElementById("attachFileBtn");
  const fileInput = document.getElementById("summarizeFileInput");
  if (!fileInput) return;

  const openPicker = (e) => { e.preventDefault(); fileInput.click(); };
  if (chip) chip.addEventListener("click", openPicker);
  if (attach) attach.addEventListener("click", openPicker);

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;

    const container = document.getElementById("chatContainer");
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    container.appendChild(createChatMessage("user", "📄 Please summarize: " + file.name, now));
    scrollChatToBottom();

    if (window.NOVA_VOICE) window.NOVA_VOICE.updateVoiceStatus("thinking");
    showTypingIndicator();

    try {
      const formData = new FormData();
      formData.append("file", file);

      const baseUrl = (typeof API_BASE_URL !== "undefined")
        ? API_BASE_URL.replace("/api", "")
        : "http://127.0.0.1:8000";

      const res = await fetch(baseUrl + "/api/summarize", {
        method: "POST",
        body: formData
      });

      let summary = "I couldn't summarize that file.";
      try {
        const data = await res.json();
        summary = data.summary || data.text || summary;
      } catch (e) { /* non-JSON */ }

      removeTypingIndicator();
      container.appendChild(createChatMessage(
        "nova", summary,
        new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      ));
      scrollChatToBottom();

      if (window.NOVA_VOICE && window.NOVA_VOICE.speakResponse) {
        window.NOVA_VOICE.speakResponse(summary);
      }
    } catch (err) {
      removeTypingIndicator();
      console.error("Summarize failed:", err);
      showToast("warning", "Summarizer unavailable", "Endpoint not connected yet.");
      container.appendChild(createChatMessage(
        "nova",
        "The summarizer isn't connected yet. Once the backend endpoint is live, I'll summarize this file for you.",
        new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      ));
      scrollChatToBottom();
    } finally {
      fileInput.value = "";
      if (window.NOVA_VOICE) window.NOVA_VOICE.updateVoiceStatus("idle");
    }
  });
}

/* ---------- Device Actions (placeholder for Person 2) ---------- */
function initDeviceActionHandler() {
  console.log("[NOVA] Device action handler ready");
}

async function handleDeviceAction(action) {
  if (!action) return;

  const enabled = localStorage.getItem("nova-agent-enabled") === "true";
  if (!enabled) {
    showToast("warning", "Agent disabled", "Enable local device control in Profile settings.");
    return;
  }

  const risky = ["open_app", "open_file", "shutdown", "delete", "run_command", "close_app"];
  const isRisky = risky.indexOf(action.type) !== -1;

  if (isRisky) {
    const ok = await confirmAction(action);
    if (!ok) { showToast("info", "Action cancelled", "No changes made."); return; }
  }

  try {
    const res = await fetch("http://127.0.0.1:5050/device/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(action)
    });
    const result = await res.json();
    showToast(
      result.success ? "success" : "error",
      result.success ? "Done" : "Action failed",
      result.message || ""
    );
  } catch (err) {
    console.error("Device action error:", err);
    showToast("error", "Device action failed", "Is the local agent running?");
  }
}

function confirmAction(action) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirmActionModal");
    const text = document.getElementById("confirmActionText");
    const yes = document.getElementById("confirmYes");
    const no = document.getElementById("confirmNo");
    if (!modal) return resolve(false);

    text.textContent = "NOVA wants to: " + (action.description || action.type || "perform an action");
    modal.classList.add("active");
    document.body.style.overflow = "hidden";

    const cleanup = () => {
      modal.classList.remove("active");
      document.body.style.overflow = "";
      yes.onclick = null;
      no.onclick = null;
    };

    yes.onclick = () => { cleanup(); resolve(true); };
    no.onclick = () => { cleanup(); resolve(false); };
  });
}

/* ---------- HTML Escape ---------- */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}