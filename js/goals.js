/* ============================================
   NOVA - Goals JavaScript (fixed)
   ============================================ */

let allGoals = [];

document.addEventListener("DOMContentLoaded", () => {
  loadGoals();
  initNewGoal();
});

async function loadGoals() {
  try {
    const result = await getGoals();
    allGoals = result.data || [];
    renderGoals();
  } catch (err) {
    console.error("Failed to load goals:", err);
    showToast("error", "Error", "Could not load goals.");
  }
}

/* Safe date formatter — handles empty strings */
function safeFormatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
}

function renderGoals() {
  const grid = document.getElementById("goalsGrid");
  if (!grid) return;

  if (!Array.isArray(allGoals) || allGoals.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <div class="empty-icon">🎯</div>
        <div class="empty-title">No goals yet</div>
        <div class="empty-text">Set your first goal and start tracking progress.</div>
      </div>
    `;
    return;
  }

  const colorCycle = ["cyan", "violet", "pink", "green"];

  grid.innerHTML = allGoals.map((g, idx) => {
    const color = g.color && ["cyan","violet","pink","green"].includes(g.color)
      ? g.color
      : colorCycle[idx % colorCycle.length];

    const progress = Math.max(0, Math.min(100, Number(g.progress) || 0));

    return `
      <div class="goal-card ${color}">
        <div class="goal-icon">🎯</div>
        <div class="goal-title">${g.title || "Untitled Goal"}</div>
        <div class="goal-category">${g.category || "General"} · Target: ${safeFormatDate(g.target)}</div>

        <div class="goal-progress-header">
          <span class="goal-progress-label">Progress</span>
          <span class="goal-progress-percent">${progress}%</span>
        </div>
        <div class="progress progress-lg">
          <div class="progress-bar" style="width: ${progress}%;"></div>
        </div>
      </div>
    `;
  }).join("");
}

function initNewGoal() {
  const btn = document.getElementById("newGoalBtn");
  const saveBtn = document.getElementById("saveGoalBtn");
  if (!btn || !saveBtn) return;

  btn.addEventListener("click", () => {
    document.getElementById("goalTitle").value = "";
    document.getElementById("goalCategory").value = "Education";
    document.getElementById("goalTarget").value = "";
    document.getElementById("goalProgress").value = "0";
    document.getElementById("goalTitleError").classList.remove("show");
    openModal("goalModal");
  });

  saveBtn.addEventListener("click", async () => {
    const title = document.getElementById("goalTitle").value.trim();
    const category = document.getElementById("goalCategory").value;
    const target = document.getElementById("goalTarget").value;
    const progressRaw = document.getElementById("goalProgress").value;
    const progress = Math.max(0, Math.min(100, Number(progressRaw) || 0));

    if (!title) {
      document.getElementById("goalTitleError").classList.add("show");
      return;
    }

    // Pick color based on count
    const colorCycle = ["cyan", "violet", "pink", "green"];
    const color = colorCycle[allGoals.length % colorCycle.length];

    try {
      const result = await createGoal({ title, category, target, progress, color });
      allGoals.unshift(result.data);
      closeModal("goalModal");
      renderGoals();
      showToast("success", "Goal created", title);
    } catch (err) {
      console.error(err);
      showToast("error", "Error", "Could not create goal.");
    }
  });
}

/* Close modal buttons */
document.addEventListener("click", (e) => {
  if (e.target.hasAttribute("data-close-modal")) {
    const modal = e.target.closest(".modal-overlay");
    if (modal) modal.classList.remove("active");
    document.body.style.overflow = "";
  }
});