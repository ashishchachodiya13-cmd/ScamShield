// ScamShield Application Controller

let currentLang = "en";
let latestAnalysis = null;
let currentRawMessage = "";
let selectedFeedbackHelpful = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  setLanguage("en");
});

/**
 * Updates UI language and re-translates all static DOM elements.
 */
function setLanguage(lang) {
  currentLang = lang;
  const strings = I18N[lang];

  // Button active styles
  document.getElementById("btn-lang-en").classList.toggle("active", lang === "en");
  document.getElementById("btn-lang-hi").classList.toggle("active", lang === "hi");

  // Header & Disclaimer
  document.getElementById("app-title-text").textContent = strings.appTitle;
  document.getElementById("app-subtitle-text").textContent = strings.appSubtitle;
  document.getElementById("lang-label-text").textContent = strings.langLabel;
  document.getElementById("disclaimer-badge-text").textContent = strings.disclaimerBadge;
  document.getElementById("disclaimer-desc-text").textContent = strings.disclaimerText;

  // Input Section
  document.getElementById("input-heading-text").textContent = strings.inputHeading;
  document.getElementById("input-subheading-text").textContent = strings.inputSubheading;
  document.getElementById("message-input").placeholder = strings.messagePlaceholder;
  document.getElementById("btn-analyze-text").textContent = strings.analyzeBtn.replace("🔍 ", "");
  document.getElementById("btn-upload-text").textContent = strings.uploadBtn.replace("📁 ", "");
  document.getElementById("btn-clear-text").textContent = strings.clearBtn;

  // OCR Review
  document.getElementById("ocr-title-text").textContent = strings.ocrHeading;
  document.getElementById("ocr-instruction-text").textContent = strings.ocrInstruction;
  document.getElementById("btn-ocr-confirm-text").textContent = strings.ocrConfirmBtn.replace("✓ ", "");
  document.getElementById("btn-ocr-cancel-text").textContent = strings.ocrCancelBtn.replace("✕ ", "");

  // Results Static Titles
  document.getElementById("cat-label-text").textContent = strings.categoryLabel;
  document.getElementById("explanation-heading-text").textContent = strings.explanationHeading;
  document.getElementById("flags-heading-text").textContent = strings.flagsHeading;
  document.getElementById("actions-heading-text").textContent = strings.actionsHeading;
  document.getElementById("dos-title-text").textContent = strings.dosTitle;
  document.getElementById("donts-title-text").textContent = strings.dontsTitle;
  document.getElementById("helplines-title-text").textContent = strings.helplinesTitle;
  document.getElementById("feedback-heading-text").textContent = strings.feedbackHeading;
  document.getElementById("feedback-subheading-text").textContent = strings.feedbackSubheading;
  document.getElementById("feedback-helpful-btn-text").textContent = strings.feedbackHelpfulBtn;
  document.getElementById("feedback-unhelpful-btn-text").textContent = strings.feedbackUnhelpfulBtn;
  document.getElementById("feedback-comment-input").placeholder = strings.feedbackCommentPlaceholder;
  document.getElementById("feedback-submit-btn-text").textContent = strings.feedbackSubmitBtn;
  document.getElementById("feedback-thanks-text").textContent = strings.feedbackThanks;
  document.getElementById("check-another-btn-text").textContent = strings.checkAnotherBtn;

  // If a result is currently active, re-analyze with the new language to translate output
  if (latestAnalysis && currentRawMessage) {
    handleAnalyze(false); // silent re-run
  }
}

/**
 * Handles screenshot file upload & OCR flow (UC3, UC4, UC5).
 */
async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const ocrBox = document.getElementById("ocr-box");
  const ocrEditor = document.getElementById("ocr-text-editor");
  const ocrPreview = document.getElementById("ocr-image-preview");
  const loading = document.getElementById("loading-spinner");
  const loadingText = document.getElementById("loading-status-text");

  // Show local preview immediately
  ocrPreview.src = URL.createObjectURL(file);
  ocrBox.style.display = "block";
  ocrEditor.value = "";

  // Show loading indicator
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
      alert(data.message || I18N[currentLang].ocrEmpty);
    }
  } catch (err) {
    loading.style.display = "none";
    alert("OCR Error: " + err.message);
  }
}

/**
 * User confirms the reviewed OCR text and proceeds to analysis (UC5).
 */
function handleConfirmOCR() {
  const ocrText = document.getElementById("ocr-text-editor").value.trim();
  if (!ocrText) {
    alert(I18N[currentLang].emptyError);
    return;
  }
  document.getElementById("message-input").value = ocrText;
  document.getElementById("ocr-box").style.display = "none";
  handleAnalyze();
}

/**
 * Cancels OCR review.
 */
function handleCancelOCR() {
  document.getElementById("ocr-box").style.display = "none";
  document.getElementById("screenshot-file").value = "";
  document.getElementById("ocr-image-preview").src = "";
  document.getElementById("ocr-text-editor").value = "";
}

/**
 * Clears main textarea.
 */
function handleClearInput() {
  document.getElementById("message-input").value = "";
  handleCancelOCR();
  document.getElementById("results-section").style.display = "none";
}

/**
 * Main analysis execution (UC1, UC7, UC8, UC9, UC10).
 */
async function handleAnalyze(scroll = true) {
  const textInput = document.getElementById("message-input");
  const rawText = textInput.value.trim();

  if (!rawText) {
    alert(I18N[currentLang].emptyError);
    textInput.focus();
    return;
  }

  currentRawMessage = rawText;
  const loading = document.getElementById("loading-spinner");
  const loadingText = document.getElementById("loading-status-text");
  const resultsSection = document.getElementById("results-section");

  loading.style.display = "block";
  loadingText.textContent = I18N[currentLang].analyzingText;

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: rawText,
        language: currentLang,
      }),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Analysis failed.");
    }

    const data = await res.json();
    latestAnalysis = data;
    loading.style.display = "none";

    renderResults(data);
    resultsSection.style.display = "block";

    if (scroll) {
      resultsSection.scrollIntoView({ behavior: "smooth" });
    }
  } catch (err) {
    loading.style.display = "none";
    alert("Error: " + err.message);
  }
}

/**
 * Renders analysis results in an accessible format.
 */
function renderResults(data) {
  const strings = I18N[currentLang];
  const riskBanner = document.getElementById("risk-banner");
  const riskIcon = document.getElementById("risk-icon");
  const riskTitle = document.getElementById("risk-level-title");
  const riskDesc = document.getElementById("risk-level-desc");

  // 1. Risk Level Banner (Color + Text Label + Icon, never color alone)
  riskBanner.className = "risk-banner";
  const isZeroFlags = (!data.matched_flags || data.matched_flags.length === 0);

  if (isZeroFlags) {
    riskBanner.classList.add("risk-low");
    riskIcon.textContent = "🛡️";
    riskTitle.textContent = strings.riskZeroTitle;
    riskDesc.textContent = strings.riskZeroSub;
  } else if (data.risk_level === "High") {
    riskBanner.classList.add("risk-high");
    riskIcon.textContent = "🚨";
    riskTitle.textContent = strings.riskHighTitle;
    riskDesc.textContent = currentLang === "hi" 
      ? "यह संदेश अत्यधिक खतरनाक और संदिग्ध है। किसी भी मांग का पालन न करें।"
      : "This message exhibits strong indicators of a scam. Do not follow any instructions.";
  } else if (data.risk_level === "Medium") {
    riskBanner.classList.add("risk-med");
    riskIcon.textContent = "⚠️";
    riskTitle.textContent = strings.riskMedTitle;
    riskDesc.textContent = currentLang === "hi"
      ? "संदेश में संदेहजनक बातें पाई गई हैं। अतिरिक्त सतर्कता बरतें।"
      : "Suspicious elements detected. Exercise high caution.";
  } else {
    riskBanner.classList.add("risk-low");
    riskIcon.textContent = "🛡️";
    riskTitle.textContent = strings.riskLowTitle;
    riskDesc.textContent = currentLang === "hi"
      ? "कम जोखिम के संकेत हैं, लेकिन हमेशा सतर्क रहें।"
      : "Low risk indicators detected. Stay cautious.";
  }

  // 2. Category & Score
  document.getElementById("result-category-name").textContent = data.category_name;
  document.getElementById("result-score-text").textContent = 
    `${strings.scoreLabel}: ${data.score} (${data.risk_level} Risk)`;

  // 3. Explanation & Source Badge
  const sourceBadge = document.getElementById("explanation-source-badge");
  sourceBadge.textContent = data.explanation_source === "llm" ? strings.sourceLlm : strings.sourceTemplate;
  document.getElementById("result-explanation-text").textContent = data.explanation;

  // 4. Matched Red Flags List
  const flagsContainer = document.getElementById("flags-container");
  flagsContainer.innerHTML = "";

  if (isZeroFlags) {
    flagsContainer.innerHTML = `<p style="font-size: 20px; color: #475569;">${strings.noFlagsFound}</p>`;
  } else {
    data.matched_flags.forEach((flag) => {
      const flagCard = document.createElement("div");
      flagCard.className = "flag-item";

      const flagName = currentLang === "hi" ? flag.name_hi : flag.name_en;
      const snippets = flag.snippets.map((s) => `<span class="flag-snippet">"${s}"</span>`).join(" ");

      flagCard.innerHTML = `
        <div class="flag-header">
          <span>🚩 ${flagName}</span>
          <span style="font-size: 17px; background: #fee2e2; padding: 2px 8px; border-radius: 4px;">
            ${currentLang === "hi" ? "अंक" : "Weight"}: +${flag.weight}
          </span>
        </div>
        <div style="margin-top: 10px; font-size: 19px;">
          <strong>${strings.matchedSnippets}</strong> ${snippets}
        </div>
      `;
      flagsContainer.appendChild(flagCard);
    });
  }

  // 5. Actions: What TO Do
  const dosList = document.getElementById("dos-list");
  dosList.innerHTML = "";
  (data.actions.dos || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    dosList.appendChild(li);
  });

  // 6. Actions: What NOT To Do
  const dontsList = document.getElementById("donts-list");
  dontsList.innerHTML = "";
  (data.actions.donts || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    dontsList.appendChild(li);
  });

  // 7. Helplines
  const helplinesList = document.getElementById("helplines-list");
  helplinesList.innerHTML = "";
  (data.actions.official_channels || []).forEach((channel) => {
    const li = document.createElement("li");
    li.textContent = channel;
    helplinesList.appendChild(li);
  });

  // Reset feedback form
  selectedFeedbackHelpful = null;
  document.getElementById("feedback-comment-container").style.display = "none";
  document.getElementById("feedback-thanks").style.display = "none";
  document.getElementById("feedback-action-row").style.display = "flex";
  document.getElementById("feedback-comment-input").value = "";
}

/**
 * User clicks Helpful or Not Helpful (UC11).
 */
function handleFeedback(isHelpful) {
  selectedFeedbackHelpful = isHelpful;
  document.getElementById("feedback-action-row").style.display = "none";
  document.getElementById("feedback-comment-container").style.display = "block";
}

/**
 * Submits feedback to backend SQLite.
 */
async function submitFeedbackComment() {
  const comment = document.getElementById("feedback-comment-input").value.trim();

  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        helpful: selectedFeedbackHelpful,
        category: latestAnalysis ? latestAnalysis.category : null,
        risk_level: latestAnalysis ? latestAnalysis.risk_level : null,
        comment: comment || null,
      }),
    });

    document.getElementById("feedback-comment-container").style.display = "none";
    document.getElementById("feedback-thanks").style.display = "block";
  } catch (err) {
    alert("Could not submit feedback: " + err.message);
  }
}

/**
 * Resets the screen to check a new message.
 */
function handleReset() {
  handleClearInput();
  window.scrollTo({ top: 0, behavior: "smooth" });
  document.getElementById("message-input").focus();
}
