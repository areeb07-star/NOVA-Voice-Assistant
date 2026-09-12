/* ============================================
   NOVA - Auth JavaScript (FIXED)
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
  console.log("[NOVA Auth] Initializing...");
  initLoginForm();
  initRegisterForm();
  initPasswordToggles();
  initPasswordStrength();
});

/* =========================================================
   LOGIN
   ========================================================= */
function initLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  console.log("[NOVA Auth] Login form found, attaching submit");

  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");
  const submitBtn = document.getElementById("loginSubmit");
  const errorBox = document.getElementById("loginError");
  const errorText = document.getElementById("loginErrorText");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    e.stopPropagation();

    console.log("[NOVA Auth] Login submitted");

    // Reset UI
    errorBox.classList.remove("show");
    clearFieldError("loginEmail");
    clearFieldError("loginPassword");

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    let valid = true;

    if (!email || !isValidEmail(email)) {
      showFieldError("loginEmail", "Please enter a valid email.");
      valid = false;
    }
    if (!password || password.length < 6) {
      showFieldError("loginPassword", "Password must be at least 6 characters.");
      valid = false;
    }

    if (!valid) {
      console.log("[NOVA Auth] Login validation failed");
      return;
    }

    submitBtn.classList.add("loading");
    submitBtn.disabled = true;

    try {
      const result = await loginUser(email, password);
      console.log("[NOVA Auth] Login result:", result);

      if (result && result.success) {
        const name = (result.data && result.data.user && result.data.user.fullName) || "User";
        setUserName(name);
        localStorage.setItem("nova-auth-token", result.data.token);

        showToast("success", "Welcome back!", "Redirecting to dashboard...");

        // Redirect — with hard fallback
        console.log("[NOVA Auth] Redirecting to dashboard.html");
        window.location.href = "dashboard.html";

        // Hard fallback in case href assignment is blocked
        setTimeout(() => {
          window.location.assign("dashboard.html");
        }, 300);
      } else {
        throw new Error("Login failed");
      }
    } catch (err) {
      console.error("[NOVA Auth] Login error:", err);
      errorText.textContent = "Invalid email or password. Please try again.";
      errorBox.classList.add("show");
      showToast("error", "Login failed", "Please check your credentials.");
      submitBtn.classList.remove("loading");
      submitBtn.disabled = false;
    }
  });

  emailInput.addEventListener("input", () => clearFieldError("loginEmail"));
  passwordInput.addEventListener("input", () => clearFieldError("loginPassword"));
}

/* =========================================================
   REGISTER
   ========================================================= */
function initRegisterForm() {
  const form = document.getElementById("registerForm");
  if (!form) return;

  console.log("[NOVA Auth] Register form found, attaching submit");

  const fullNameInput = document.getElementById("regFullName");
  const emailInput = document.getElementById("regEmail");
  const usernameInput = document.getElementById("regUsername");
  const passwordInput = document.getElementById("regPassword");
  const confirmInput = document.getElementById("regConfirmPassword");
  const submitBtn = document.getElementById("registerSubmit");
  const errorBox = document.getElementById("registerError");
  const errorText = document.getElementById("registerErrorText");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    e.stopPropagation();

    console.log("[NOVA Auth] Register submitted");

    errorBox.classList.remove("show");
    ["regFullName", "regEmail", "regUsername", "regPassword", "regConfirmPassword"]
      .forEach(clearFieldError);

    const fullName = fullNameInput.value.trim();
    const email = emailInput.value.trim();
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmInput.value;

    let valid = true;

    if (!fullName || fullName.length < 2) {
      showFieldError("regFullName", "Please enter your full name.");
      valid = false;
    }
    if (!email || !isValidEmail(email)) {
      showFieldError("regEmail", "Please enter a valid email.");
      valid = false;
    }
    if (!username || username.length < 3) {
      showFieldError("regUsername", "Username must be at least 3 characters.");
      valid = false;
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      showFieldError("regUsername", "Only letters, numbers, and underscores allowed.");
      valid = false;
    }
    if (!password || password.length < 8) {
      showFieldError("regPassword", "Password must be at least 8 characters.");
      valid = false;
    } else if (!/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
      showFieldError("regPassword", "Include at least 1 uppercase letter and 1 number.");
      valid = false;
    }
    if (password !== confirmPassword) {
      showFieldError("regConfirmPassword", "Passwords do not match.");
      valid = false;
    }

    if (!valid) {
      console.log("[NOVA Auth] Register validation failed");
      return;
    }

    submitBtn.classList.add("loading");
    submitBtn.disabled = true;

    try {
      const result = await registerUser({ fullName, email, username, password });
      console.log("[NOVA Auth] Register result:", result);

      if (result && result.success) {
        setUserName(fullName);
        localStorage.setItem("nova-auth-token", result.data.token);

        showToast("success", "Account created!", "Welcome to NOVA.");

        console.log("[NOVA Auth] Redirecting to dashboard.html");
        window.location.href = "dashboard.html";

        setTimeout(() => {
          window.location.assign("dashboard.html");
        }, 300);
      } else {
        throw new Error("Registration failed");
      }
    } catch (err) {
      console.error("[NOVA Auth] Register error:", err);
      errorText.textContent = "Registration failed. Please try again.";
      errorBox.classList.add("show");
      showToast("error", "Registration failed", "Please try again.");
      submitBtn.classList.remove("loading");
      submitBtn.disabled = false;
    }
  });

  [
    ["regFullName", fullNameInput],
    ["regEmail", emailInput],
    ["regUsername", usernameInput],
    ["regPassword", passwordInput],
    ["regConfirmPassword", confirmInput]
  ].forEach(([id, input]) => {
    input.addEventListener("input", () => clearFieldError(id));
  });
}

/* =========================================================
   PASSWORD TOGGLES
   ========================================================= */
function initPasswordToggles() {
  const toggles = [
    { btn: "toggleLoginPassword", input: "loginPassword" },
    { btn: "toggleRegPassword", input: "regPassword" },
    { btn: "toggleRegConfirmPassword", input: "regConfirmPassword" }
  ];

  toggles.forEach(({ btn, input }) => {
    const toggleBtn = document.getElementById(btn);
    const inputEl = document.getElementById(input);
    if (!toggleBtn || !inputEl) return;

    toggleBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isPassword = inputEl.type === "password";
      inputEl.type = isPassword ? "text" : "password";
      toggleBtn.textContent = isPassword ? "🙈" : "👁️";
      toggleBtn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
    });
  });
}

/* =========================================================
   PASSWORD STRENGTH
   ========================================================= */
function initPasswordStrength() {
  const passwordInput = document.getElementById("regPassword");
  const strengthBar = document.getElementById("passwordStrength");
  if (!passwordInput || !strengthBar) return;

  const segments = strengthBar.querySelectorAll(".password-strength-segment");
  const label = document.getElementById("passwordStrengthLabel");

  passwordInput.addEventListener("input", () => {
    const password = passwordInput.value;
    const strength = calculatePasswordStrength(password);

    segments.forEach((seg, i) => {
      seg.classList.remove("active", "weak", "fair", "good", "strong");
      if (i < strength.score) seg.classList.add("active", strength.level);
    });

    label.textContent = strength.label;
    label.style.color = strength.color;
  });
}

function calculatePasswordStrength(password) {
  if (!password) return { score: 0, level: "", label: "—", color: "var(--text-dim)" };

  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const capped = Math.min(score, 4);
  const levels = [
    { level: "weak",   label: "Weak",   color: "var(--accent-red)" },
    { level: "weak",   label: "Weak",   color: "var(--accent-red)" },
    { level: "fair",   label: "Fair",   color: "var(--accent-amber)" },
    { level: "good",   label: "Good",   color: "var(--accent-blue)" },
    { level: "strong", label: "Strong", color: "var(--accent-green)" }
  ];

  return { score: capped, ...levels[capped] };
}

/* =========================================================
   HELPERS
   ========================================================= */
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showFieldError(fieldId, message) {
  const input = document.getElementById(fieldId);
  const error = document.getElementById(fieldId + "Error");
  if (input) input.classList.add("error");
  if (error) {
    error.textContent = message;
    error.classList.add("show");
  }
}

function clearFieldError(fieldId) {
  const input = document.getElementById(fieldId);
  const error = document.getElementById(fieldId + "Error");
  if (input) input.classList.remove("error");
  if (error) error.classList.remove("show");
}