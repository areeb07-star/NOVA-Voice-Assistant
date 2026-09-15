/* ============================================
   NOVA - Study Plans JavaScript
   ============================================ */

let allStudyPlans = [];

document.addEventListener("DOMContentLoaded", () => {
  loadStudyPlans();
  initCreatePlan();
});

async function loadStudyPlans() {
  try {
    const result = await getStudyPlans();
    allStudyPlans = result.data;
    renderStudyPlans();
  } catch (err) {
    console.error("Failed to load study plans:", err);
  }
}

function renderStudyPlans() {
  const grid = document.getElementById("studyPlansGrid");
  if (!grid) return;

  if (allStudyPlans.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <div class="empty-icon">📚</div>
        <div class="empty-title">No study plans yet</div>
        <div class="empty-text">Create your first study plan to get started.</div>
      </div>
    `;
    return;
  }

  grid.innerHTML = allStudyPlans.map((plan) => `
    <div class="study-plan-card">
      <div class="study-plan-subject">${plan.subject}</div>
      <div class="study-plan-meta">
        Exam: ${plan.examDate ? formatDate(plan.examDate) : "Not set"} · 
        Daily: ${plan.dailyTime || "—"}
      </div>

      <div class="study-progress-header">
        <span class="study-progress-label">Progress</span>
        <span class="study-progress-percent">${plan.progress}%</span>
      </div>
      <div class="progress">
        <div class="progress-bar" style="width: ${plan.progress}%;"></div>
      </div>

      <div class="study-timeline">
        ${(plan.timeline || []).map((t) => `
          <div class="timeline-item">
            <span class="timeline-day">${t.day}</span>
            <span class="timeline-dot ${t.status}"></span>
            <span class="timeline-topic ${t.status}">${t.topic}</span>
            <span class="timeline-status">${t.status === "today" ? "→ Today" : t.status === "completed" ? "✓" : ""}</span>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

function initCreatePlan() {
  const btn = document.getElementById("createStudyPlanBtn");
  const saveBtn = document.getElementById("saveStudyPlanBtn");
  if (!btn || !saveBtn) return;

  btn.addEventListener("click", () => {
    document.getElementById("planSubject").value = "";
    document.getElementById("planExamDate").value = "";
    document.getElementById("planTopics").value = "";
    document.getElementById("planDailyTime").value = "1 hour";
    openModal("studyPlanModal");
  });

  saveBtn.addEventListener("click", async () => {
    const subject = document.getElementById("planSubject").value.trim();
    const examDate = document.getElementById("planExamDate").value;
    const topicsRaw = document.getElementById("planTopics").value.trim();
    const dailyTime = document.getElementById("planDailyTime").value.trim();

    if (!subject) {
      document.getElementById("planSubjectError").classList.add("show");
      return;
    }

    const topics = topicsRaw ? topicsRaw.split(",").map((t) => t.trim()).filter(Boolean) : [];

    const result = await createStudyPlan({
      subject,
      examDate,
      topics,
      dailyTime,
      progress: 0,
      timeline: topics.slice(0, 5).map((topic, i) => ({
        day: ["MON", "TUE", "WED", "THU", "FRI"][i] || "SAT",
        topic,
        status: i === 0 ? "today" : "upcoming"
      }))
    });

    allStudyPlans.unshift(result.data);
    closeModal("studyPlanModal");
    renderStudyPlans();
    showToast("success", "Study plan created", subject);
  });
}

document.addEventListener("click", (e) => {
  if (e.target.hasAttribute("data-close-modal")) {
    const modal = e.target.closest(".modal-overlay");
    if (modal) modal.classList.remove("active");
    document.body.style.overflow = "";
  }
});