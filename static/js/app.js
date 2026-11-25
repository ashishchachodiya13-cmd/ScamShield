/**
 * ScamShield — Application Controller (Stage 4)
 * Architecture:
 * - AuthManager: User sessions, JWT cookies, profile updates, account deletion
 * - Router: Hash-based client routing with protected route guards
 * - PreferencesManager: Senior Citizen Large Text mode, Language switch
 * - ScanController: Message analysis, OCR review, results rendering, feedback
 * - Toast: Accessible toast notifications
 */

// Application State
let currentLang = "en";
let currentUser = null;
let currentPreferences = { large_text: false, retain_masked_text: false, language: "en" };
let currentRawMessage = "";
let latestAnalysis = null;
let selectedFeedbackHelpful = null;

// =============================================================================
// 1. Initialization
// =============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  // 1. Initialize language & large text from localStorage
  const savedLang = localStorage.getItem("scamshield_lang") || "en";
  const savedLargeText = localStorage.getItem("scamshield_large_text") === "true";
  
  if (savedLargeText) {
    document.documentElement.classList.add("large-text-mode");
    const toggleEl = document.getElementById("setting-large-text-toggle");
    if (toggleEl) toggleEl.checked = true;
    updateLargeTextBtnUI(true);
  }

  setLanguage(savedLang, false);

  // 2. Check Auth State from API
  await checkAuthState();

  // 3. Initialize Router
  window.addEventListener("hashchange", handleHashChange);
  handleHashChange();
});

// =============================================================================
// 2. Toast Notification Manager
// =============================================================================
function showToast(message, type = "info", duration = 4000) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "alert");

  let iconSvg = "";
  if (type === "success") {
    iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
  } else if (type === "error") {
    iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
  } else if (type === "warning") {
    iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
  } else {
    iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
  }

  toast.innerHTML = `
    <span class="toast-icon">${iconSvg}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button type="button" class="toast-close" aria-label="Close alert" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "toast-out 0.25s forwards";
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// =============================================================================
// 3. Auth Manager
// =============================================================================
async function checkAuthState() {
  try {
    const res = await fetch("/api/auth/me", {
      method: "GET",
      headers: { "Accept": "application/json" }
    });

    if (res.ok) {
      const data = await res.json();
      currentUser = data.user;
      currentPreferences = data.preferences || currentPreferences;
      updateAuthUI(true);
      applyPreferences(currentPreferences);
    } else {
      currentUser = null;
      updateAuthUI(false);
    }
  } catch (err) {
    currentUser = null;
    updateAuthUI(false);
  }
}

function updateAuthUI(isLoggedIn) {
  const userBlock = document.getElementById("sidebar-user-block");
  const guestBlock = document.getElementById("sidebar-guest-block");
  const profileLinks = document.querySelectorAll(".auth-only");

  if (isLoggedIn && currentUser) {
    if (userBlock) userBlock.style.display = "flex";
    if (guestBlock) guestBlock.style.display = "none";
    profileLinks.forEach(el => el.style.display = "flex");

    const initials = currentUser.name
      ? currentUser.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2)
      : "SS";
    
    const avatarEl = document.getElementById("sidebar-user-avatar");
    const nameEl = document.getElementById("sidebar-user-name");
    const emailEl = document.getElementById("sidebar-user-email");
    if (avatarEl) avatarEl.textContent = initials;
    if (nameEl) nameEl.textContent = currentUser.name;
    if (emailEl) emailEl.textContent = currentUser.email;

    // Profile page inputs
    const profEmail = document.getElementById("profile-email-readonly");
    const profName = document.getElementById("profile-name-input");
    if (profEmail) profEmail.value = currentUser.email;
    if (profName) profName.value = currentUser.name;
  } else {
    if (userBlock) userBlock.style.display = "none";
    if (guestBlock) guestBlock.style.display = "block";
    profileLinks.forEach(el => el.style.display = "none");
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const rememberMe = document.getElementById("login-remember-me").checked;
  const btn = document.getElementById("btn-login-submit");

  if (!email || !password) return;

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, remember_me: rememberMe })
    });

    const data = await res.json();
    btn.classList.remove("is-loading");

    if (res.ok) {
      currentUser = data.user;
      showToast(data.message || "Logged in successfully!", "success");
      updateAuthUI(true);
      await checkAuthState();
      navigateTo("scan");
    } else {
      showToast(data.detail || "Invalid email or password.", "error");
    }
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

async function handleSignupSubmit(event) {
  event.preventDefault();
  const name = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const confirm = document.getElementById("signup-confirm-password").value;
  const btn = document.getElementById("btn-signup-submit");

  if (password !== confirm) {
    showToast("Passwords do not match.", "error");
    return;
  }

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name, password })
    });

    const data = await res.json();
    btn.classList.remove("is-loading");

    if (res.ok) {
      showToast(data.message || "Account created successfully! Please log in.", "success");
      navigateTo("login");
      // Auto-fill login email
      const loginEmailInput = document.getElementById("login-email");
      if (loginEmailInput) loginEmailInput.value = email;
    } else {
      showToast(data.detail || "Registration could not be completed.", "error");
    }
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
  } catch (e) {
    // continue cleanup
  }
  currentUser = null;
  updateAuthUI(false);
  showToast("Logged out successfully.", "info");
  navigateTo("scan");
}

async function handleForgotSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("forgot-email").value.trim();
  const btn = document.getElementById("btn-forgot-submit");
  if (!email) return;

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    btn.classList.remove("is-loading");
    showToast(data.message || "If the email is registered, password reset instructions have been logged.", "info", 6000);
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

async function handleResetSubmit(event) {
  event.preventDefault();
  const token = document.getElementById("reset-token").value.trim();
  const password = document.getElementById("reset-password").value;
  const confirm = document.getElementById("reset-confirm-password").value;
  const btn = document.getElementById("btn-reset-submit");

  if (!token) {
    showToast("Invalid or missing reset token.", "error");
    return;
  }
  if (password !== confirm) {
    showToast("Passwords do not match.", "error");
    return;
  }

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: password })
    });
    const data = await res.json();
    btn.classList.remove("is-loading");

    if (res.ok) {
      showToast(I18N[currentLang].resetSuccessMsg, "success", 5000);
      navigateTo("login");
    } else {
      showToast(data.detail || "Password reset token is invalid or expired.", "error");
    }
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

async function handleUpdateName(event) {
  event.preventDefault();
  const name = document.getElementById("profile-name-input").value.trim();
  const btn = document.getElementById("btn-save-name");
  if (!name) return;

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    const data = await res.json();
    btn.classList.remove("is-loading");

    if (res.ok) {
      currentUser = data.user;
      updateAuthUI(true);
      showToast(data.message || "Profile updated successfully.", "success");
    } else {
      showToast(data.detail || "Could not update profile.", "error");
    }
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

async function handleChangePassword(event) {
  event.preventDefault();
  const old_password = document.getElementById("profile-current-password").value;
  const new_password = document.getElementById("profile-new-password").value;
  const btn = document.getElementById("btn-change-pwd");

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old_password, new_password })
    });
    const data = await res.json();
    btn.classList.remove("is-loading");

    if (res.ok) {
      showToast(data.message || "Password changed successfully.", "success");
      document.getElementById("profile-current-password").value = "";
      document.getElementById("profile-new-password").value = "";
    } else {
      showToast(data.detail || "Failed to change password.", "error");
    }
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

async function handleDeleteAccount() {
  const password = document.getElementById("delete-confirm-password").value;
  const btn = document.getElementById("btn-confirm-delete");

  if (!password) {
    showToast("Please enter your password to confirm.", "error");
    return;
  }

  btn.classList.add("is-loading");
  try {
    const res = await fetch("/api/auth/me", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password })
    });
    const data = await res.json();
    btn.classList.remove("is-loading");

    if (res.ok) {
      toggleDeleteModal(false);
      currentUser = null;
      updateAuthUI(false);
      showToast(data.message || "Account permanently deleted.", "info", 5000);
      navigateTo("scan");
    } else {
      showToast(data.detail || "Password verification failed.", "error");
    }
  } catch (err) {
    btn.classList.remove("is-loading");
    showToast(I18N[currentLang].errorGeneric, "error");
  }
}

// =============================================================================
// 4. Hash Router & Navigation
// =============================================================================
function handleHashChange() {
  const rawHash = window.location.hash.slice(1) || "scan";
  let [route, queryString] = rawHash.split("?");
  route = route.toLowerCase();

  // Route Guards for Protected Views
  const protectedRoutes = ["profile", "dashboard", "history", "reports"];
  if (protectedRoutes.includes(route) && !currentUser) {
    showToast("Please log in to access this feature.", "info");
    navigateTo("login");
    return;
  }

  // Active Topbar Title & Navigation sync
  const strings = I18N[currentLang];
  const topbarTitle = document.getElementById("topbar-view-title");

  // Hide all views
  document.querySelectorAll(".page-view").forEach(v => v.style.display = "none");
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".bottom-nav-link").forEach(el => el.classList.remove("active"));

  // Check if route is an auth subview
  const authRoutes = ["login", "signup", "forgot-password", "reset-password"];
  if (authRoutes.includes(route)) {
    const authView = document.getElementById("view-auth");
    if (authView) authView.style.display = "block";
    showAuthSubview(route, queryString);
    if (topbarTitle) topbarTitle.textContent = strings.navLogin;
    toggleMobileDrawer(false);
    return;
  }

  // Standard Page Views
  const targetView = document.getElementById(`view-${route}`);
  if (targetView) {
    targetView.style.display = "block";
  } else {
    // Fallback to scan
    document.getElementById("view-scan").style.display = "block";
    route = "scan";
  }

  // Sidebar link active state
  const activeNav = document.getElementById(`nav-link-${route}`);
  if (activeNav) activeNav.classList.add("active");

  // Mobile bottom nav link active state
  const activeBottomNav = document.getElementById(`bnav-${route}`);
  if (activeBottomNav) activeBottomNav.classList.add("active");

  // Title sync
  if (topbarTitle) {
    const titleMap = {
      scan: strings.navScan,
      mobile: strings.navMobile,
      dashboard: strings.navOverview,
      history: strings.navHistory,
      reports: strings.navReports,
      settings: strings.navSettings,
      profile: strings.navProfile
    };
    topbarTitle.textContent = titleMap[route] || strings.navScan;
  }

  // Trigger page-specific data loaders
  if (route === "dashboard") {
    loadDashboardStats();
    loadSecurityTips();
  } else if (route === "history") {
    loadHistory(1);
    populateCategoryFilter();
  } else if (route === "reports") {
    loadReports(currentReportsRange);
  }

  toggleMobileDrawer(false);
}

function showAuthSubview(route, queryString) {
  document.querySelectorAll(".auth-subview").forEach(el => el.style.display = "none");

  if (route === "login") {
    document.getElementById("subview-login").style.display = "block";
  } else if (route === "signup") {
    document.getElementById("subview-signup").style.display = "block";
  } else if (route === "forgot-password") {
    document.getElementById("subview-forgot").style.display = "block";
  } else if (route === "reset-password") {
    document.getElementById("subview-reset").style.display = "block";
    if (queryString) {
      const params = new URLSearchParams(queryString);
      const token = params.get("token");
      if (token) {
        document.getElementById("reset-token").value = token;
      }
    }
  }
}

function navigateTo(route) {
  window.location.hash = `#${route}`;
}

// =============================================================================
// 5. Preferences & Accessibility (Senior Citizen Large Text Mode)
// =============================================================================
function toggleLargeTextMode(forcedState) {
  const isLarge = forcedState !== undefined
    ? forcedState
    : !document.documentElement.classList.contains("large-text-mode");

  if (isLarge) {
    document.documentElement.classList.add("large-text-mode");
  } else {
    document.documentElement.classList.remove("large-text-mode");
  }

  localStorage.setItem("scamshield_large_text", isLarge ? "true" : "false");
  updateLargeTextBtnUI(isLarge);

  const toggleEl = document.getElementById("setting-large-text-toggle");
  if (toggleEl) toggleEl.checked = isLarge;

  // Persist preference to DB if logged in
  if (currentUser) {
    saveUserPreferences({ large_text: isLarge });
  }
}

function updateLargeTextBtnUI(isLarge) {
  const btn = document.getElementById("btn-toggle-large-text");
  if (!btn) return;
  btn.setAttribute("aria-pressed", isLarge ? "true" : "false");
  btn.classList.toggle("btn-primary", isLarge);
  btn.classList.toggle("btn-outline", !isLarge);
}

function applyPreferences(prefs) {
  if (!prefs) return;
  if (prefs.large_text) {
    toggleLargeTextMode(true);
  }
  if (prefs.retain_masked_text !== undefined) {
    const el = document.getElementById("setting-retain-masked-toggle");
    if (el) el.checked = Boolean(prefs.retain_masked_text);
  }
  if (prefs.language && (prefs.language === "en" || prefs.language === "hi")) {
    setLanguage(prefs.language, false);
  }
}

async function handleRetainMaskedToggle(checked) {
  if (currentUser) {
    await saveUserPreferences({ retain_masked_text: checked });
    showToast(checked ? "Masked text retention enabled." : "Masked text retention disabled.", "info");
  } else {
    showToast("Please log in to save data retention preferences.", "info");
  }
}

async function saveUserPreferences(partial) {
  try {
    const res = await fetch("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(partial)
    });
    if (res.ok) {
      const data = await res.json();
      currentPreferences = data.preferences;
      const note = document.getElementById("settings-status-note");
      if (note) {
        note.style.display = "inline";
        setTimeout(() => note.style.display = "none", 3000);
      }
    }
  } catch (err) {
    console.error("Preferences save error", err);
  }
}

// =============================================================================
// 6. Internationalization (Bilingual EN / HI)
// =============================================================================
function setLanguage(lang, persist = true) {
  currentLang = lang;
  if (persist) {
    localStorage.setItem("scamshield_lang", lang);
    if (currentUser) {
      saveUserPreferences({ language: lang });
    }
  }

  const s = I18N[lang] || I18N.en;

  // Header & Topbar buttons
  const btnEn = document.getElementById("btn-lang-en");
  const btnHi = document.getElementById("btn-lang-hi");
  if (btnEn && btnHi) {
    if (lang === "en") {
      btnEn.style.background = "var(--indigo-600)";
      btnEn.style.color = "#ffffff";
      btnHi.style.background = "var(--bg-card)";
      btnHi.style.color = "var(--text-secondary)";
    } else {
      btnHi.style.background = "var(--indigo-600)";
      btnHi.style.color = "#ffffff";
      btnEn.style.background = "var(--bg-card)";
      btnEn.style.color = "var(--text-secondary)";
    }
  }

  // Brand and Shell
  setElemText("sidebar-brand-title", s.appTitle);
  setElemText("nav-text-scan", s.navScan);
  setElemText("nav-text-mobile", s.navMobile);
  setElemText("nav-text-overview", s.navOverview);
  setElemText("nav-text-history", s.navHistory);
  setElemText("nav-text-reports", s.navReports);
  setElemText("nav-text-settings", s.navSettings);
  setElemText("nav-text-profile", s.navProfile);
  setElemText("sidebar-guest-notice", s.guestNotice);
  setElemText("sidebar-btn-login", s.navLogin);
  setElemText("sidebar-btn-signup", s.navSignup);
  setElemText("topbar-large-text-btn", lang === "hi" ? "बड़े अक्षर" : "Large Text");

  // Mobile Bottom Nav
  setElemText("bnav-text-dashboard", s.navOverview);
  setElemText("bnav-text-scan", s.navScan);
  setElemText("bnav-text-history", s.navHistory);
  setElemText("bnav-text-settings", s.navSettings);

  // Scan View
  setElemText("disclaimer-badge-text", s.disclaimerBadge + ":");
  setElemText("disclaimer-desc-text", s.disclaimerText);
  setElemText("input-heading-text", s.inputHeading);
  setElemText("input-subheading-text", s.inputSubheading);
  const msgInput = document.getElementById("message-input");
  if (msgInput) msgInput.placeholder = s.messagePlaceholder;
  setElemText("btn-upload-text", s.uploadBtn);
  setElemText("btn-clear-text", s.clearBtn);
  setElemText("btn-analyze-text", s.analyzeBtn);
  setElemText("loading-status-text", s.analyzingText);

  // OCR
  setElemText("ocr-title-text", s.ocrHeading);
  setElemText("ocr-instruction-text", s.ocrInstruction);
  setElemText("btn-ocr-confirm-text", s.ocrConfirmBtn);
  setElemText("btn-ocr-cancel-text", s.ocrCancelBtn);

  // Result static headers
  setElemText("cat-label-text", s.categoryLabel);
  setElemText("explanation-heading-text", s.explanationHeading);
  setElemText("flags-heading-text", s.flagsHeading);
  setElemText("actions-heading-text", s.actionsHeading);
  setElemText("dos-title-text", s.dosTitle);
  setElemText("donts-title-text", s.dontsTitle);
  setElemText("helplines-title-text", s.helplinesTitle);
  setElemText("feedback-heading-text", s.feedbackHeading);
  setElemText("feedback-subheading-text", s.feedbackSubheading);
  setElemText("feedback-helpful-btn-text", s.feedbackHelpfulBtn);
  setElemText("feedback-unhelpful-btn-text", s.feedbackUnhelpfulBtn);
  const fbInput = document.getElementById("feedback-comment-input");
  if (fbInput) fbInput.placeholder = s.feedbackCommentPlaceholder;
  setElemText("feedback-submit-btn-text", s.feedbackSubmitBtn);
  setElemText("feedback-thanks-text", s.feedbackThanks);
  setElemText("check-another-btn-text", s.checkAnotherBtn);

  // Auth Showcase
  setElemText("auth-showcase-tag", s.authShowcaseTag);
  setElemText("auth-showcase-subtitle", s.authShowcaseSubtitle);
  setElemText("auth-feature-1", s.authFeature1);
  setElemText("auth-feature-2", s.authFeature2);
  setElemText("auth-feature-3", s.authFeature3);
  setElemText("auth-trust-badge", s.authTrustBadge);

  // Auth: Login
  setElemText("login-title", s.loginTitle);
  setElemText("login-subtitle", s.loginSubtitle);
  setElemText("login-email-label", s.emailLabel);
  setElemText("login-pwd-label", s.passwordLabel);
  setElemText("login-forgot-link", s.forgotPasswordLink);
  setElemText("login-remember-label", s.rememberMe);
  setElemText("btn-login-text", s.loginBtn);
  setElemText("login-no-account-text", s.noAccountPrompt);
  setElemText("login-signup-link", s.signupLink);

  // Auth: Sign Up
  setElemText("signup-title", s.signupTitle);
  setElemText("signup-subtitle", s.signupSubtitle);
  setElemText("signup-name-label", s.nameLabel);
  setElemText("signup-email-label", s.emailLabel);
  setElemText("signup-pwd-label", s.passwordLabel);
  setElemText("signup-confirm-pwd-label", s.confirmPasswordLabel);
  setElemText("btn-signup-text", s.signupBtn);
  setElemText("signup-have-account-text", s.haveAccountPrompt);
  setElemText("signup-login-link", s.loginLink);
  setElemText("strength-caption-label", s.pwdStrengthLabel);
  setElemText("rule-len-text", s.pwdRule1);
  setElemText("rule-num-text", s.pwdRule2);
  setElemText("rule-email-text", s.pwdRule3);

  // Auth: Forgot & Reset
  setElemText("forgot-title", s.forgotTitle);
  setElemText("forgot-subtitle", s.forgotSubtitle);
  setElemText("forgot-email-label", s.emailLabel);
  setElemText("btn-forgot-text", s.sendResetBtn);
  setElemText("forgot-back-link", s.backToLogin);
  setElemText("reset-title", s.resetTitle);
  setElemText("reset-subtitle", s.resetSubtitle);
  setElemText("reset-new-pwd-label", s.newPasswordLabel);
  setElemText("reset-confirm-pwd-label", s.confirmNewPasswordLabel);
  setElemText("btn-reset-text", s.resetBtn);
  setElemText("reset-back-link", s.backToLogin);

  // Profile View
  setElemText("profile-title", s.profileTitle);
  setElemText("profile-subtitle", s.profileSubtitle);
  setElemText("profile-details-heading", s.profileDetailsHeading);
  setElemText("profile-email-label", s.registeredEmailLabel);
  setElemText("profile-name-label", s.fullNameLabel);
  setElemText("profile-save-name-btn", s.updateNameBtn);
  setElemText("profile-pwd-heading", s.changePwdHeading);
  setElemText("profile-current-pwd-label", s.currentPwdLabel);
  setElemText("profile-new-pwd-label", s.newPwdLabel);
  setElemText("profile-change-pwd-btn", s.updatePwdBtn);
  setElemText("profile-danger-heading", s.dangerZoneHeading);
  setElemText("profile-delete-title", s.deleteAccountTitle);
  setElemText("profile-delete-desc", s.deleteAccountDesc);
  setElemText("profile-delete-btn", s.deleteAccountBtn);
  setElemText("delete-modal-title", s.deleteModalTitle);
  setElemText("delete-modal-desc-text", s.deleteModalDesc);
  setElemText("delete-modal-pwd-label", s.deleteModalPwdConfirm);
  setElemText("delete-modal-cancel-btn", s.cancelBtn);
  setElemText("delete-modal-confirm-btn", s.confirmDeleteBtn);

  // Settings View
  setElemText("settings-title", s.settingsTitle);
  setElemText("settings-subtitle", s.settingsSubtitle);
  setElemText("settings-appearance-heading", s.appearanceHeading);
  setElemText("settings-large-text-title", s.largeTextTitle);
  setElemText("settings-large-text-desc", s.largeTextDesc);
  setElemText("settings-lang-title", s.languageSettingTitle);
  setElemText("settings-lang-desc", s.languageSettingDesc);
  setElemText("settings-privacy-heading", s.privacyHeading);
  setElemText("settings-retain-masked-title", s.retainMaskedTitle);
  setElemText("settings-retain-masked-desc", s.retainMaskedDesc);

  // Dashboard View (Stage 5)
  setElemText("dashboard-heading", s.dashboardTitle);
  setElemText("dashboard-subheading", s.dashboardSubtitle);
  setElemText("stat-total-label", s.statTotalScans);
  setElemText("stat-high-label", s.statHighRisk);
  setElemText("stat-med-label", s.statMedRisk);
  setElemText("stat-low-label", s.statLowRisk);
  setElemText("chart-risk-heading", s.riskDistributionTitle);
  setElemText("chart-cat-heading", s.categoriesTitle);
  setElemText("recent-scans-heading", s.recentScansTitle);
  setElemText("dashboard-empty-title", s.noDataYet);
  setElemText("dashboard-empty-desc", s.scanFirstPrompt);
  setElemText("dashboard-empty-btn", s.scanNowBtn);
  renderCurrentTip();

  // History View (Stage 6)
  setElemText("history-heading", s.historyTitle);
  setElemText("history-subheading", s.historySubtitle);
  setElemText("opt-risk-all", s.filterRiskAll);
  setElemText("opt-risk-high", s.filterRiskHigh);
  setElemText("opt-risk-med", s.filterRiskMed);
  setElemText("opt-risk-low", s.filterRiskLow);
  setElemText("opt-cat-all", s.filterCatAll);
  const histSearch = document.getElementById("history-search");
  if (histSearch) histSearch.placeholder = s.searchHistoryPlaceholder;
  setElemText("btn-clear-history-text", s.clearAllHistoryBtn);
  setElemText("history-empty-title", s.historyEmptyTitle);
  setElemText("history-empty-desc", s.historyEmptyDesc);
  setElemText("drawer-header-title", s.drawerTitle);
  setElemText("btn-delete-drawer-text", s.deleteRecordBtn);
  setElemText("th-date", s.colDate);
  setElemText("th-risk", s.colRisk);
  setElemText("th-cat", s.colCategory);
  setElemText("th-score", s.colScore);
  setElemText("th-action", s.colActions);

  // Reports View (Stage 6)
  setElemText("reports-heading", s.reportsTitle);
  setElemText("reports-subheading", s.reportsSubtitle);
  setElemText("tab-range-week", s.rangeWeek);
  setElemText("tab-range-month", s.rangeMonth);
  setElemText("tab-range-all", s.rangeAll);
  setElemText("rep-label-ratio", s.highRiskRatioLabel);
  setElemText("reports-timeline-heading", s.activityTimelineTitle);
  setElemText("export-card-heading", s.exportDataHeading);
  setElemText("btn-export-csv-text", s.exportCsvBtn);
  setElemText("btn-export-json-text", s.exportJsonBtn);

  // Mobile View (Stage 7)
  setElemText("mobile-heading", s.mobileTitle);
  setElemText("mobile-subheading", s.mobileSubtitle);
  setElemText("pwa-title", s.pwaInstallTitle);
  setElemText("pwa-desc", s.pwaInstallDesc);
  setElemText("btn-pwa-install-text", s.pwaInstallBtn);
  setElemText("android-guide-heading", s.androidShareTitle);
  setElemText("guide-step-1", s.androidShareStep1);
  setElemText("guide-step-2", s.androidShareStep2);
  setElemText("guide-step-3", s.androidShareStep3);
  setElemText("multi-upload-heading", s.multiUploadTitle);
  setElemText("multi-upload-sub", s.multiUploadDesc);
  setElemText("dropzone-text", s.dropzonePrompt);
  setElemText("btn-batch-analyze-text", s.analyzeBatchBtn);
  setElemText("platform-notice-heading", s.platformNoticeTitle + ":");
  setElemText("platform-notice-text", s.platformNoticeDesc);

  // Re-render analysis if currently visible
  if (latestAnalysis && currentRawMessage) {
    handleAnalyze(false);
  }
}

function setElemText(id, text) {
  const el = document.getElementById(id);
  if (el && text) el.textContent = text;
}

// =============================================================================
// 7. Scanner & OCR (UC1, UC3, UC4, UC5, UC9, UC10)
// =============================================================================
async function handleAnalyze(scroll = true) {
  const textInput = document.getElementById("message-input");
  const rawText = textInput.value.trim();

  if (!rawText) {
    showToast(I18N[currentLang].emptyError, "warning");
    textInput.focus();
    return;
  }

  currentRawMessage = rawText;
  const loading = document.getElementById("loading-spinner");
  const resultsSection = document.getElementById("results-section");

  if (loading) loading.style.display = "block";
  if (resultsSection) resultsSection.style.display = "none";

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: rawText,
        language: currentLang,
        source: "text"
      }),
    });

    if (loading) loading.style.display = "none";

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Analysis failed.");
    }

    const data = await res.json();
    latestAnalysis = data;

    renderResults(data);
    if (resultsSection) resultsSection.style.display = "flex";

    if (scroll && resultsSection) {
      resultsSection.scrollIntoView({ behavior: "smooth" });
    }
  } catch (err) {
    if (loading) loading.style.display = "none";
    showToast(err.message, "error");
  }
}

function renderResults(data) {
  const strings = I18N[currentLang];
  const riskBanner = document.getElementById("risk-banner");
  const riskIcon = document.getElementById("risk-icon");
  const riskTitle = document.getElementById("risk-level-title");
  const riskDesc = document.getElementById("risk-level-desc");

  // 1. Risk Level Banner (Color + Text + SVG Icon)
  riskBanner.className = "risk-banner-card";
  const isZeroFlags = (!data.matched_flags || data.matched_flags.length === 0);

  if (isZeroFlags) {
    riskBanner.classList.add("risk-zero");
    riskIcon.innerHTML = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>`;
    riskTitle.textContent = strings.riskZeroTitle;
    riskDesc.textContent = strings.riskZeroSub;
  } else if (data.risk_level === "High") {
    riskBanner.classList.add("risk-high");
    riskIcon.innerHTML = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    riskTitle.textContent = strings.riskHighTitle;
    riskDesc.textContent = currentLang === "hi"
      ? "यह संदेश अत्यधिक खतरनाक और संदिग्ध है। किसी भी मांग का पालन न करें।"
      : "This message exhibits strong indicators of a scam. Do not follow any instructions.";
  } else if (data.risk_level === "Medium") {
    riskBanner.classList.add("risk-med");
    riskIcon.innerHTML = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
    riskTitle.textContent = strings.riskMedTitle;
    riskDesc.textContent = currentLang === "hi"
      ? "संदेश में संदेहजनक बातें पाई गई हैं। अतिरिक्त सतर्कता बरतें।"
      : "Suspicious elements detected. Exercise high caution.";
  } else {
    riskBanner.classList.add("risk-low");
    riskIcon.innerHTML = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`;
    riskTitle.textContent = strings.riskLowTitle;
    riskDesc.textContent = currentLang === "hi"
      ? "कम जोखिम के संकेत हैं, लेकिन हमेशा सतर्क रहें।"
      : "Low risk indicators detected. Stay cautious.";
  }

  // 2. Category & Score
  setElemText("result-category-name", data.category_name);
  setElemText("result-score-text", `${strings.scoreLabel}: ${data.score} (${data.risk_level} Risk)`);

  // 3. Explanation & Source Badge
  const sourceBadge = document.getElementById("explanation-source-badge");
  if (sourceBadge) {
    sourceBadge.className = `source-badge ${data.explanation_source === "llm" ? "source-llm" : "source-template"}`;
    sourceBadge.textContent = data.explanation_source === "llm" ? strings.sourceLlm : strings.sourceTemplate;
  }
  setElemText("result-explanation-text", data.explanation);

  // 4. Matched Red Flags
  const flagsContainer = document.getElementById("flags-container");
  if (flagsContainer) {
    flagsContainer.innerHTML = "";
    if (isZeroFlags) {
      flagsContainer.innerHTML = `<p style="color: var(--text-tertiary);">${strings.noFlagsFound}</p>`;
    } else {
      data.matched_flags.forEach(flag => {
        const flagCard = document.createElement("div");
        flagCard.className = "flag-item-card";

        const flagName = currentLang === "hi" ? flag.name_hi : flag.name_en;
        const snippets = flag.snippets.map(s => `<span class="snippet-chip">"${escapeHtml(s)}"</span>`).join(" ");

        flagCard.innerHTML = `
          <div class="flag-header-row">
            <span class="flag-name-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>
              ${escapeHtml(flagName)}
            </span>
            <span class="badge badge-risk-high">${currentLang === "hi" ? "अंक" : "Weight"}: +${flag.weight}</span>
          </div>
          <div class="flag-snippets-wrap">
            <strong>${strings.matchedSnippets}</strong> ${snippets || "—"}
          </div>
        `;
        flagsContainer.appendChild(flagCard);
      });
    }
  }

  // 5. Actions: What TO Do
  const dosList = document.getElementById("dos-list");
  if (dosList) {
    dosList.innerHTML = "";
    const dos = (data.actions && data.actions.dos) || [];
    dos.forEach(item => {
      const li = document.createElement("li");
      li.innerHTML = `<span>✓</span><span>${escapeHtml(item)}</span>`;
      dosList.appendChild(li);
    });
  }

  // 6. Actions: What NOT To Do (Avoid)
  const dontsList = document.getElementById("donts-list");
  if (dontsList) {
    dontsList.innerHTML = "";
    const donts = (data.actions && data.actions.donts) || data.avoid || [];
    donts.forEach(item => {
      const li = document.createElement("li");
      li.innerHTML = `<span>✕</span><span>${escapeHtml(item)}</span>`;
      dontsList.appendChild(li);
    });
  }

  // 7. Official Emergency Helplines
  const helplinesList = document.getElementById("helplines-list");
  if (helplinesList) {
    helplinesList.innerHTML = "";
    const channels = (data.actions && data.actions.official_channels) || data.reporting_channels || [];
    channels.forEach(ch => {
      const li = document.createElement("li");
      li.className = "helpline-item";

      // Make URLs or Phone numbers interactive
      const phoneMatch = ch.match(/\b(1930|1909|112)\b/);
      const urlMatch = ch.match(/https?:\/\/[^\s]+/);

      if (phoneMatch) {
        li.innerHTML = `📞 <a href="tel:${phoneMatch[0]}">${escapeHtml(ch)}</a>`;
      } else if (urlMatch) {
        li.innerHTML = `🌐 <a href="${urlMatch[0]}" target="_blank" rel="noopener noreferrer">${escapeHtml(ch)} ↗</a>`;
      } else {
        li.textContent = `• ${ch}`;
      }
      helplinesList.appendChild(li);
    });
  }

  // Reset feedback box state
  const commentBox = document.getElementById("feedback-comment-container");
  const thanksBox = document.getElementById("feedback-thanks");
  if (commentBox) commentBox.style.display = "none";
  if (thanksBox) thanksBox.style.display = "none";
  selectedFeedbackHelpful = null;
}

// Screenshot OCR
async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const ocrBox = document.getElementById("ocr-box");
  const ocrEditor = document.getElementById("ocr-text-editor");
  const ocrPreview = document.getElementById("ocr-image-preview");
  const loading = document.getElementById("loading-spinner");
  const loadingText = document.getElementById("loading-status-text");

  ocrPreview.src = URL.createObjectURL(file);
  ocrBox.style.display = "block";
  ocrEditor.value = "";

  loading.style.display = "block";
  loadingText.textContent = I18N[currentLang].ocrProcessing;

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/ocr", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    loading.style.display = "none";

    if (data.success && data.extracted_text) {
      ocrEditor.value = data.extracted_text;
      ocrEditor.focus();
    } else {
      ocrEditor.value = "";
      showToast(data.message || I18N[currentLang].ocrEmpty, "warning");
    }
  } catch (err) {
    loading.style.display = "none";
    showToast("OCR Error: " + err.message, "error");
  }
}

function handleConfirmOCR() {
  const ocrText = document.getElementById("ocr-text-editor").value.trim();
  if (!ocrText) {
    showToast(I18N[currentLang].emptyError, "warning");
    return;
  }
  document.getElementById("message-input").value = ocrText;
  document.getElementById("ocr-box").style.display = "none";
  handleAnalyze();
}

function handleCancelOCR() {
  document.getElementById("ocr-box").style.display = "none";
  document.getElementById("screenshot-file").value = "";
  document.getElementById("ocr-image-preview").src = "";
  document.getElementById("ocr-text-editor").value = "";
}

function handleClearInput() {
  document.getElementById("message-input").value = "";
  handleCancelOCR();
  const resSec = document.getElementById("results-section");
  if (resSec) resSec.style.display = "none";
  latestAnalysis = null;
  currentRawMessage = "";
}

function handleReset() {
  handleClearInput();
  window.scrollTo({ top: 0, behavior: "smooth" });
  document.getElementById("message-input").focus();
}

// Feedback
async function handleFeedback(helpful) {
  selectedFeedbackHelpful = helpful;
  const commentBox = document.getElementById("feedback-comment-container");
  if (commentBox) commentBox.style.display = "block";

  if (!latestAnalysis) return;
  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        helpful: helpful,
        category: latestAnalysis.category,
        risk_level: latestAnalysis.risk_level,
        analysis_id: latestAnalysis.analysis_id || null
      })
    });
  } catch (err) {
    // silently catch
  }
}

async function submitFeedbackComment() {
  const comment = document.getElementById("feedback-comment-input").value.trim();
  const thanks = document.getElementById("feedback-thanks");
  const commentBox = document.getElementById("feedback-comment-container");

  if (!latestAnalysis || selectedFeedbackHelpful === null) return;

  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        helpful: selectedFeedbackHelpful,
        category: latestAnalysis.category,
        risk_level: latestAnalysis.risk_level,
        comment: comment,
        analysis_id: latestAnalysis.analysis_id || null
      })
    });
    if (commentBox) commentBox.style.display = "none";
    if (thanks) thanks.style.display = "block";
  } catch (err) {
    showToast("Feedback error", "error");
  }
}

// =============================================================================
// 8. Password Strength & UI Utilities
// =============================================================================
function updatePasswordStrength(password) {
  const meter = document.getElementById("pwd-strength-meter");
  const scoreLabel = document.getElementById("strength-score-label");
  const ruleLen = document.getElementById("rule-len");
  const ruleNum = document.getElementById("rule-num");
  const ruleEmail = document.getElementById("rule-email");
  const emailInput = document.getElementById("signup-email");
  const email = emailInput ? emailInput.value.toLowerCase().trim() : "";

  let score = 0;
  const isLen = password.length >= 8;
  const isNotAllNum = !/^\d+$/.test(password);
  const isNotEmail = !email || !password.toLowerCase().includes(email);

  if (ruleLen) ruleLen.className = isLen ? "valid" : "";
  if (ruleNum) ruleNum.className = (isLen && isNotAllNum) ? "valid" : "";
  if (ruleEmail) ruleEmail.className = (isLen && isNotEmail) ? "valid" : "";

  if (isLen) score++;
  if (isLen && isNotAllNum && isNotEmail) score++;
  if (score >= 2 && /[A-Z]/.test(password) && /[a-z]/.test(password) && /\d/.test(password)) score++;
  if (score >= 3 && /[^A-Za-z0-9]/.test(password)) score++;

  if (meter) meter.setAttribute("data-score", String(score));

  const strings = I18N[currentLang];
  const labels = [
    currentLang === "hi" ? "अति संक्षिप्त" : "Too short",
    strings.pwdWeak,
    strings.pwdFair,
    strings.pwdGood,
    strings.pwdStrong
  ];

  if (scoreLabel) scoreLabel.textContent = labels[score];
}

function togglePasswordVisibility(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

function toggleMobileDrawer(open) {
  const sidebar = document.getElementById("app-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar) return;

  if (open) {
    sidebar.classList.add("is-open");
    if (backdrop) backdrop.classList.add("is-open");
  } else {
    sidebar.classList.remove("is-open");
    if (backdrop) backdrop.classList.remove("is-open");
  }
}

function toggleDeleteModal(open) {
  const modal = document.getElementById("delete-modal");
  const pwdInput = document.getElementById("delete-confirm-password");
  if (!modal) return;

  if (open) {
    modal.classList.add("is-open");
    if (pwdInput) {
      pwdInput.value = "";
      setTimeout(() => pwdInput.focus(), 100);
    }
  } else {
    modal.classList.remove("is-open");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// =============================================================================
// 9. Dashboard Controller & Security Tips (Stage 5)
// =============================================================================
let riskDoughnutChart = null;
let categoryBarChart = null;
let securityTipsList = [];
let currentTipIndex = 0;
let tipRotationTimer = null;

async function loadDashboardStats() {
  try {
    const res = await fetch("/api/stats/overview", { headers: { "Accept": "application/json" } });
    if (!res.ok) return;
    const data = await res.json();

    const emptyState = document.getElementById("dashboard-empty-state");
    const dataContainer = document.getElementById("dashboard-data-container");

    if (data.total_scans === 0) {
      if (emptyState) emptyState.style.display = "block";
      if (dataContainer) dataContainer.style.display = "none";
      return;
    }

    if (emptyState) emptyState.style.display = "none";
    if (dataContainer) dataContainer.style.display = "block";

    setElemText("stat-total-val", String(data.total_scans));
    setElemText("stat-high-val", String(data.high_risk_count));
    setElemText("stat-med-val", String(data.medium_risk_count));
    setElemText("stat-low-val", String(data.low_risk_count));

    // Fallback tables for accessibility
    setElemText("tbl-risk-high", String(data.high_risk_count));
    setElemText("tbl-risk-med", String(data.medium_risk_count));
    setElemText("tbl-risk-low", String(data.low_risk_count));

    const catTbody = document.getElementById("table-cat-tbody");
    if (catTbody && data.category_distribution) {
      catTbody.innerHTML = data.category_distribution.map(c => `
        <tr><td>${escapeHtml(c.category_name || c.category)}</td><td>${c.count}</td></tr>
      `).join("");
    }

    // Chart.js - Risk Doughnut Chart
    if (typeof Chart !== "undefined") {
      const ctxRisk = document.getElementById("chart-risk-doughnut");
      if (ctxRisk) {
        if (riskDoughnutChart) riskDoughnutChart.destroy();
        riskDoughnutChart = new Chart(ctxRisk, {
          type: "doughnut",
          data: {
            labels: [
              currentLang === "hi" ? "अत्यधिक जोखिम" : "High Risk",
              currentLang === "hi" ? "मध्यम जोखिम" : "Medium Risk",
              currentLang === "hi" ? "कम जोखिम" : "Low Risk"
            ],
            datasets: [{
              data: [data.high_risk_count, data.medium_risk_count, data.low_risk_count],
              backgroundColor: ["#DC2626", "#D97706", "#059669"],
              borderWidth: 2,
              borderColor: "#ffffff"
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: "bottom", labels: { boxWidth: 12 } }
            }
          }
        });
      }

      // Chart.js - Category Bar Chart
      const ctxCat = document.getElementById("chart-category-bar");
      if (ctxCat && data.category_distribution) {
        if (categoryBarChart) categoryBarChart.destroy();
        const catLabels = data.category_distribution.map(c => c.category_name || c.category);
        const catCounts = data.category_distribution.map(c => c.count);
        categoryBarChart = new Chart(ctxCat, {
          type: "bar",
          data: {
            labels: catLabels,
            datasets: [{
              label: currentLang === "hi" ? "जांच संख्या" : "Scans Count",
              data: catCounts,
              backgroundColor: "#4F46E5",
              borderRadius: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: { legend: { display: false } },
            scales: {
              x: { beginAtZero: true, ticks: { precision: 0 } },
              y: { ticks: { autoSkip: false } }
            }
          }
        });
      }
    }

    // Recent Scans Table
    const recentTbody = document.getElementById("recent-scans-tbody");
    if (recentTbody && data.recent_scans) {
      if (data.recent_scans.length === 0) {
        recentTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-tertiary); padding: var(--space-4);">No recent scans</td></tr>`;
      } else {
        recentTbody.innerHTML = data.recent_scans.map(s => {
          const badgeClass = s.risk_level === "High" ? "risk-high" : (s.risk_level === "Medium" ? "risk-med" : "risk-low");
          const dateStr = s.created_at ? new Date(s.created_at).toLocaleDateString(currentLang === "hi" ? "hi-IN" : "en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-";
          return `
            <tr>
              <td>${escapeHtml(dateStr)}</td>
              <td><span class="badge ${badgeClass}">${escapeHtml(s.risk_level)}</span></td>
              <td style="font-weight: 600;">${escapeHtml(s.category_name || s.category)}</td>
              <td><span class="score-badge-pill">${s.score}</span></td>
              <td><button type="button" class="btn btn-sm btn-outline" onclick="openHistoryDetail(${s.id})">${I18N[currentLang].viewDetailsBtn || "View"}</button></td>
            </tr>
          `;
        }).join("");
      }
    }
  } catch (err) {
    console.error("Dashboard stats load error", err);
  }
}

async function loadSecurityTips() {
  if (securityTipsList.length === 0) {
    try {
      const res = await fetch("/api/security-tips");
      if (res.ok) {
        securityTipsList = await res.json();
      }
    } catch (e) {
      return;
    }
  }
  renderCurrentTip();
  if (!tipRotationTimer && securityTipsList.length > 1) {
    tipRotationTimer = setInterval(() => {
      currentTipIndex = (currentTipIndex + 1) % securityTipsList.length;
      renderCurrentTip();
    }, 10000);
  }
}

function renderCurrentTip() {
  if (securityTipsList.length === 0) return;
  const tip = securityTipsList[currentTipIndex];
  const source = currentLang === "hi" ? (tip.source_hi || tip.source) : tip.source;
  const title = currentLang === "hi" ? (tip.title_hi || tip.title_en) : tip.title_en;
  const desc = currentLang === "hi" ? (tip.tip_hi || tip.tip_en) : tip.tip_en;

  setElemText("tip-source-text", source);
  setElemText("tip-title-text", title);
  setElemText("tip-body-text", desc);
  setElemText("tip-counter", `${currentTipIndex + 1} / ${securityTipsList.length}`);
}

function handleNextTip() {
  if (securityTipsList.length === 0) return;
  currentTipIndex = (currentTipIndex + 1) % securityTipsList.length;
  renderCurrentTip();
}

function handlePrevTip() {
  if (securityTipsList.length === 0) return;
  currentTipIndex = (currentTipIndex - 1 + securityTipsList.length) % securityTipsList.length;
  renderCurrentTip();
}

// =============================================================================
// 10. History Controller & Detail Drawer (Stage 6)
// =============================================================================
let currentHistoryPage = 1;
let totalHistoryPages = 1;
let historySearchDebounce = null;
let currentDrawerAnalysisId = null;

function populateCategoryFilter() {
  const select = document.getElementById("history-filter-category");
  if (!select || select.options.length > 1) return;

  const knownCats = [
    { id: "digital_arrest", name_en: "Digital Arrest Scam", name_hi: "डिजिटल अरेस्ट फ्रॉड" },
    { id: "fake_bank_phishing", name_en: "Fake Bank / Phishing", name_hi: "फर्जी बैंक / फिशिंग लिंक" },
    { id: "investment_fraud", name_en: "Investment / Trading Fraud", name_hi: "निवेश / शेयर ट्रेडिंग फ्रॉड" },
    { id: "upi_collect_fraud", name_en: "UPI Collect Request Fraud", name_hi: "यूपीआई कलेक्ट फ्रॉड" },
    { id: "lottery_prize", name_en: "Lottery / Prize Scam", name_hi: "लॉटरी / इनाम फ्रॉड" },
    { id: "kyc_expiry", name_en: "KYC / SIM Expiry Threat", name_hi: "केवाईसी / सिम बंद होने की धमकी" },
    { id: "electricity_bill", name_en: "Electricity Bill Disconnection", name_hi: "बिजली बिल भुगतान फ्रॉड" },
    { id: "job_offer", name_en: "Part-Time Job Scam", name_hi: "पार्ट-टाइम नौकरी फ्रॉड" },
    { id: "family_emergency", name_en: "Family Emergency Scam", name_hi: "पारिवारिक दुर्घटना फ्रॉड" },
    { id: "impersonation_govt", name_en: "Government Impersonation", name_hi: "सरकारी अधिकारी की झूठी पहचान" }
  ];

  knownCats.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = currentLang === "hi" ? c.name_hi : c.name_en;
    select.appendChild(opt);
  });
}

async function loadHistory(page = 1) {
  currentHistoryPage = page;
  const risk = document.getElementById("history-filter-risk")?.value || "";
  const cat = document.getElementById("history-filter-category")?.value || "";
  const search = document.getElementById("history-search")?.value.trim() || "";

  let url = `/api/history?page=${page}&page_size=10`;
  if (risk) url += `&risk=${encodeURIComponent(risk)}`;
  if (cat) url += `&category=${encodeURIComponent(cat)}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await fetch(url, { headers: { "Accept": "application/json" } });
    if (!res.ok) return;
    const data = await res.json();

    const emptyState = document.getElementById("history-empty-state");
    const tableCard = document.getElementById("history-table-card");

    if (data.total === 0) {
      if (emptyState) emptyState.style.display = "block";
      if (tableCard) tableCard.style.display = "none";
      return;
    }

    if (emptyState) emptyState.style.display = "none";
    if (tableCard) tableCard.style.display = "block";

    totalHistoryPages = data.total_pages || 1;
    setElemText("history-page-info", currentLang === "hi"
      ? `पृष्ठ ${data.page} / ${totalHistoryPages} (कुल ${data.total} रिकॉर्ड)`
      : `Page ${data.page} of ${totalHistoryPages} (${data.total} total)`
    );

    const prevBtn = document.getElementById("btn-hist-prev");
    const nextBtn = document.getElementById("btn-hist-next");
    if (prevBtn) prevBtn.disabled = data.page <= 1;
    if (nextBtn) nextBtn.disabled = data.page >= totalHistoryPages;

    const tbody = document.getElementById("history-tbody");
    if (tbody) {
      tbody.innerHTML = data.items.map(item => {
        const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString(currentLang === "hi" ? "hi-IN" : "en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-";
        const badgeClass = item.risk_level === "High" ? "risk-high" : (item.risk_level === "Medium" ? "risk-med" : "risk-low");
        return `
          <tr>
            <td>${escapeHtml(dateStr)}</td>
            <td><span class="badge ${badgeClass}">${escapeHtml(item.risk_level)}</span></td>
            <td style="font-weight: 600;">${escapeHtml(item.category_name || item.category)}</td>
            <td><span class="score-badge-pill">${item.score}</span></td>
            <td><span style="font-size: var(--font-size-xs); color: var(--text-tertiary); text-transform: uppercase;">${escapeHtml(item.source || "text")}</span></td>
            <td>
              <button type="button" class="btn btn-sm btn-outline" onclick="openHistoryDetail(${item.id})">
                ${I18N[currentLang].viewDetailsBtn || "View"}
              </button>
            </td>
          </tr>
        `;
      }).join("");
    }
  } catch (err) {
    console.error("Load history error", err);
  }
}

function changeHistoryPage(delta) {
  const targetPage = currentHistoryPage + delta;
  if (targetPage >= 1 && targetPage <= totalHistoryPages) {
    loadHistory(targetPage);
  }
}

function debounceHistorySearch() {
  clearTimeout(historySearchDebounce);
  historySearchDebounce = setTimeout(() => {
    loadHistory(1);
  }, 350);
}

async function openHistoryDetail(id) {
  currentDrawerAnalysisId = id;
  const drawer = document.getElementById("history-detail-drawer");
  const backdrop = document.getElementById("drawer-backdrop");
  const body = document.getElementById("drawer-content-body");
  const dateTimeEl = document.getElementById("drawer-date-time");

  if (!drawer || !backdrop || !body) return;

  drawer.classList.add("is-open");
  backdrop.classList.add("is-open");
  body.innerHTML = `<div style="text-align: center; padding: var(--space-8);"><div class="spinner" style="margin: 0 auto; width: 32px; height: 32px; border: 3px solid var(--navy-200); border-top-color: var(--indigo-600); border-radius: 50%; animation: btn-spin 0.8s linear infinite;"></div></div>`;

  try {
    const res = await fetch(`/api/history/${id}`, { headers: { "Accept": "application/json" } });
    if (!res.ok) {
      body.innerHTML = `<p style="color: var(--danger-600);">Could not load details.</p>`;
      return;
    }
    const item = await res.json();
    const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : "";
    if (dateTimeEl) dateTimeEl.textContent = dateStr;

    const badgeClass = item.risk_level === "High" ? "risk-high" : (item.risk_level === "Medium" ? "risk-med" : "risk-low");

    let flagsHtml = "";
    if (item.matched_flags && item.matched_flags.length > 0) {
      flagsHtml = item.matched_flags.map(f => `
        <div class="flag-item-card" style="margin-bottom: var(--space-2);">
          <div class="flag-name-title">⚠️ ${escapeHtml(currentLang === "hi" ? f.name_hi : f.name_en)}</div>
        </div>
      `).join("");
    } else {
      flagsHtml = `<p style="font-size: var(--font-size-sm); color: var(--text-tertiary);">No specific flags recorded.</p>`;
    }

    let dosHtml = "";
    if (item.actions?.dos && item.actions.dos.length > 0) {
      dosHtml = item.actions.dos.map(d => `<li>✓ ${escapeHtml(d)}</li>`).join("");
    }
    let dontsHtml = "";
    if (item.actions?.donts && item.actions.donts.length > 0) {
      dontsHtml = item.actions.donts.map(d => `<li>✕ ${escapeHtml(d)}</li>`).join("");
    }

    let retainedTextHtml = "";
    if (item.masked_text) {
      retainedTextHtml = `
        <div style="background-color: var(--navy-50); border: 1px dashed var(--navy-300); border-radius: var(--radius-md); padding: var(--space-3); margin-top: var(--space-3);">
          <div style="font-size: var(--font-size-xs); font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Retained Masked Text</div>
          <div style="font-size: var(--font-size-sm); font-family: var(--font-mono); color: var(--navy-900); margin-top: 4px;">${escapeHtml(item.masked_text)}</div>
        </div>
      `;
    }

    body.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);">
        <span class="badge ${badgeClass}" style="font-size: var(--font-size-sm);">${escapeHtml(item.risk_level)}</span>
        <span class="score-badge-pill">${currentLang === "hi" ? "संदेह अंक" : "Score"}: ${item.score}</span>
      </div>

      <div>
        <h4 style="font-size: var(--font-size-lg); font-weight: 700; color: var(--navy-900); margin-top: var(--space-2);">${escapeHtml(item.category_name)}</h4>
      </div>

      ${retainedTextHtml}

      <div class="explanation-card" style="padding: var(--space-4);">
        <div style="font-weight: 700; font-size: var(--font-size-sm); color: var(--navy-900); margin-bottom: 4px;">${I18N[currentLang].explanationHeading}</div>
        <p style="font-size: var(--font-size-sm); color: var(--text-secondary); line-height: 1.5;">${escapeHtml(item.explanation)}</p>
      </div>

      <div>
        <div style="font-weight: 700; font-size: var(--font-size-sm); margin-bottom: var(--space-2);">${I18N[currentLang].flagsHeading}</div>
        ${flagsHtml}
      </div>

      <div class="actions-grid" style="grid-template-columns: 1fr; gap: var(--space-3);">
        <div class="action-column dos-col" style="padding: var(--space-3);">
          <div class="action-col-header" style="font-size: var(--font-size-sm); margin-bottom: var(--space-2);">${I18N[currentLang].dosTitle}</div>
          <ul class="action-checklist">${dosHtml}</ul>
        </div>
        <div class="action-column donts-col" style="padding: var(--space-3);">
          <div class="action-col-header" style="font-size: var(--font-size-sm); margin-bottom: var(--space-2);">${I18N[currentLang].dontsTitle}</div>
          <ul class="action-checklist">${dontsHtml}</ul>
        </div>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<p style="color: var(--danger-600);">Error loading details.</p>`;
  }
}

function closeHistoryDrawer() {
  const drawer = document.getElementById("history-detail-drawer");
  const backdrop = document.getElementById("drawer-backdrop");
  if (drawer) drawer.classList.remove("is-open");
  if (backdrop) backdrop.classList.remove("is-open");
  currentDrawerAnalysisId = null;
}

async function handleDeleteHistoryItem() {
  if (!currentDrawerAnalysisId) return;
  if (!confirm(I18N[currentLang].confirmDeleteRecord || "Delete this scan from your history?")) return;

  try {
    const res = await fetch(`/api/history/${currentDrawerAnalysisId}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Record deleted from history.", "info");
      closeHistoryDrawer();
      loadHistory(currentHistoryPage);
    } else {
      showToast("Could not delete record.", "error");
    }
  } catch (e) {
    showToast("Error deleting record.", "error");
  }
}

async function handleClearAllHistory() {
  if (!confirm(I18N[currentLang].confirmClearHistory || "Are you sure you want to delete ALL your historical scans?")) return;

  try {
    const res = await fetch("/api/history?confirm=true", { method: "DELETE" });
    if (res.ok) {
      showToast("All history wiped successfully.", "info");
      loadHistory(1);
    } else {
      showToast("Could not clear history.", "error");
    }
  } catch (e) {
    showToast("Error clearing history.", "error");
  }
}

// =============================================================================
// 11. Reports & Analytics Controller (Stage 6)
// =============================================================================
let currentReportsRange = "week";
let reportsTimelineChart = null;
let reportsCategoryChart = null;

function setReportsRange(range) {
  currentReportsRange = range;
  document.querySelectorAll(".range-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.id === `tab-range-${range}`);
  });
  loadReports(range);
}

async function loadReports(range = "week") {
  try {
    const res = await fetch(`/api/stats/reports?range=${range}`, { headers: { "Accept": "application/json" } });
    if (!res.ok) return;
    const data = await res.json();

    setElemText("rep-stat-total", String(data.total_scans));
    setElemText("rep-stat-high", String(data.high_risk_count));
    setElemText("rep-stat-ratio", `${data.high_risk_percentage}%`);
    setElemText("rep-stat-low", String(data.low_risk_count));

    // Timeline Chart
    if (typeof Chart !== "undefined") {
      const ctxTimeline = document.getElementById("chart-reports-timeline");
      if (ctxTimeline && data.activity_timeline) {
        if (reportsTimelineChart) reportsTimelineChart.destroy();
        reportsTimelineChart = new Chart(ctxTimeline, {
          type: "bar",
          data: {
            labels: data.activity_timeline.map(t => t.date),
            datasets: [
              { label: "High Risk", data: data.activity_timeline.map(t => t.high), backgroundColor: "#DC2626" },
              { label: "Medium Risk", data: data.activity_timeline.map(t => t.medium), backgroundColor: "#D97706" },
              { label: "Low Risk", data: data.activity_timeline.map(t => t.low), backgroundColor: "#059669" }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } }
          }
        });
      }

      // Category breakdown chart
      const ctxCat = document.getElementById("chart-reports-categories");
      if (ctxCat && data.category_breakdown) {
        if (reportsCategoryChart) reportsCategoryChart.destroy();
        reportsCategoryChart = new Chart(ctxCat, {
          type: "doughnut",
          data: {
            labels: data.category_breakdown.map(c => c.category),
            datasets: [{
              data: data.category_breakdown.map(c => c.count),
              backgroundColor: ["#4F46E5", "#06B6D4", "#8B5CF6", "#F59E0B", "#EC4899", "#10B981", "#3B82F6"]
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: "bottom", labels: { boxWidth: 10 } } }
          }
        });
      }
    }

    // Fallback tables
    const timelineTbody = document.getElementById("table-timeline-tbody");
    if (timelineTbody && data.activity_timeline) {
      timelineTbody.innerHTML = data.activity_timeline.map(t => `
        <tr><td>${escapeHtml(t.date)}</td><td>${t.total}</td><td>${t.high}</td><td>${t.medium}</td><td>${t.low}</td></tr>
      `).join("");
    }
    const catTbody = document.getElementById("table-reports-cat-tbody");
    if (catTbody && data.category_breakdown) {
      catTbody.innerHTML = data.category_breakdown.map(c => `
        <tr><td>${escapeHtml(c.category)}</td><td>${c.count}</td><td>${c.percentage}%</td></tr>
      `).join("");
    }
  } catch (err) {
    console.error("Reports load error", err);
  }
}

function exportData(format) {
  window.location.href = `/api/reports/export?format=${format}`;
}

// =============================================================================
// 12. Mobile & PWA Batch Screenshot Controller (Stage 7)
// =============================================================================
let deferredPwaPrompt = null;
let selectedMultiFiles = [];

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPwaPrompt = e;
  const card = document.getElementById("pwa-install-card");
  if (card) card.style.display = "flex";
});

function triggerPWAInstall() {
  if (deferredPwaPrompt) {
    deferredPwaPrompt.prompt();
    deferredPwaPrompt.userChoice.then(() => {
      deferredPwaPrompt = null;
    });
  } else {
    showToast("To install ScamShield, tap the 3 dots in your mobile browser menu and select 'Add to Home screen' or 'Install App'.", "info", 6000);
  }
}

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById("multi-dropzone")?.classList.add("dragover");
}

function handleDragLeave(e) {
  e.preventDefault();
  document.getElementById("multi-dropzone")?.classList.remove("dragover");
}

function handleFileDrop(e) {
  e.preventDefault();
  document.getElementById("multi-dropzone")?.classList.remove("dragover");
  if (e.dataTransfer?.files) {
    addMultiFiles(Array.from(e.dataTransfer.files));
  }
}

function handleMultiFilesSelected(e) {
  if (e.target.files) {
    addMultiFiles(Array.from(e.target.files));
  }
}

function addMultiFiles(files) {
  const validFiles = files.filter(f => f.type.startsWith("image/") && f.size <= 5 * 1024 * 1024);
  if (validFiles.length < files.length) {
    showToast("Some files were skipped (only images up to 5MB are supported).", "warning");
  }
  selectedMultiFiles = selectedMultiFiles.concat(validFiles).slice(0, 5);
  renderMultiPreview();
}

function removeMultiFile(index) {
  selectedMultiFiles.splice(index, 1);
  renderMultiPreview();
}

function renderMultiPreview() {
  const grid = document.getElementById("multi-preview-grid");
  const analyzeBtn = document.getElementById("btn-batch-analyze");
  if (!grid || !analyzeBtn) return;

  if (selectedMultiFiles.length === 0) {
    grid.style.display = "none";
    analyzeBtn.style.display = "none";
    return;
  }

  grid.style.display = "grid";
  analyzeBtn.style.display = "inline-flex";

  grid.innerHTML = selectedMultiFiles.map((file, idx) => {
    const url = URL.createObjectURL(file);
    return `
      <div class="multi-preview-item">
        <img src="${url}" alt="Screenshot ${idx + 1}">
        <button type="button" class="multi-preview-remove" onclick="removeMultiFile(${idx})" title="Remove">✕</button>
      </div>
    `;
  }).join("");
}

async function handleBatchAnalyze() {
  if (selectedMultiFiles.length === 0) return;
  const btn = document.getElementById("btn-batch-analyze");
  btn.classList.add("is-loading");

  showToast("Processing multiple screenshots with OCR...", "info");
  let combinedText = "";

  for (let i = 0; i < selectedMultiFiles.length; i++) {
    const file = selectedMultiFiles[i];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/ocr", { method: "POST", body: formData });
      const data = await res.json();
      if (data.extracted_text) {
        combinedText += "\n" + data.extracted_text;
      }
    } catch (e) {
      console.warn("OCR batch error on item", i);
    }
  }

  btn.classList.remove("is-loading");

  if (!combinedText.trim()) {
    showToast("Could not extract readable text from the uploaded images. Please paste the message directly.", "error");
    return;
  }

  // Switch to Scan view and execute analysis
  navigateTo("scan");
  const msgInput = document.getElementById("message-input");
  if (msgInput) {
    msgInput.value = combinedText.trim();
    handleAnalyze();
  }
}

