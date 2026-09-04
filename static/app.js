
let currentThreadId =
  localStorage.getItem("research_thread_id") || null;

let currentProgressInterval = null;

let waitingForReview = false;


// ==========================================
// PROMPTS
// ==========================================

function setPrompt(text) {

  const input =
    document.getElementById("queryInput");

  input.value = text;

  input.focus();
}


// ==========================================
// STATUS
// ==========================================

function setStatus(
  text,
  type = "ready"
) {

  const badge =
    document.getElementById("statusBadge");

  const statusText =
    document.getElementById("statusText");

  statusText.textContent = text;

  badge.className =
    `status-pill ${type}`;
}


// ==========================================
// LOADING
// ==========================================

function setLoading(isLoading) {

  const button =
    document.getElementById(
      "researchButton"
    );

  const buttonText =
    document.getElementById(
      "buttonText"
    );

  const buttonLoader =
    document.getElementById(
      "buttonLoader"
    );

  button.disabled = isLoading;

  if (isLoading) {

    buttonText.classList.add(
      "hidden"
    );

    buttonLoader.classList.remove(
      "hidden"
    );

  } else {

    buttonText.classList.remove(
      "hidden"
    );

    buttonLoader.classList.add(
      "hidden"
    );
  }
}


// ==========================================
// ERROR
// ==========================================

function showError(message) {

  const errorBox =
    document.getElementById(
      "errorBox"
    );

  errorBox.textContent = message;

  errorBox.classList.remove(
    "hidden"
  );

  errorBox.scrollIntoView({
    behavior: "smooth",
    block: "center"
  });
}


function hideError() {

  const errorBox =
    document.getElementById(
      "errorBox"
    );

  errorBox.classList.add(
    "hidden"
  );

  errorBox.textContent = "";
}


// ==========================================
// MARKDOWN
// ==========================================

function renderMarkdown(
  element,
  markdown
) {

  if (
    typeof marked !==
    "undefined"
  ) {

    element.innerHTML =
      marked.parse(
        markdown || ""
      );

  } else {

    element.innerText =
      markdown || "";
  }
}


// ==========================================
// PROGRESS ANIMATION
// ==========================================

const PROGRESS_STEPS = [

  "progress-guardrail",

  "progress-research",

  "progress-risk",

  "progress-fact",

  "progress-report"

];


function resetProgress() {

  PROGRESS_STEPS.forEach(
    (stepId) => {

      const step =
        document.getElementById(
          stepId
        );

      step.classList.remove(
        "active"
      );

      step.classList.remove(
        "completed"
      );

    }
  );
}


function startProgressAnimation() {

  stopProgressAnimation();

  resetProgress();

  const runningSection =
    document.getElementById(
      "runningSection"
    );

  runningSection.classList.remove(
    "hidden"
  );


  let currentStep = 0;


  function activateStep(index) {

    PROGRESS_STEPS.forEach(
      (
        stepId,
        stepIndex
      ) => {

        const step =
          document.getElementById(
            stepId
          );

        step.classList.remove(
          "active"
        );

        if (
          stepIndex < index
        ) {

          step.classList.add(
            "completed"
          );

        } else {

          step.classList.remove(
            "completed"
          );
        }

      }
    );


    const activeStep =
      document.getElementById(
        PROGRESS_STEPS[index]
      );

    activeStep.classList.add(
      "active"
    );
  }


  activateStep(
    currentStep
  );


  currentProgressInterval =
    setInterval(
      () => {

        currentStep++;

        if (
          currentStep >=
          PROGRESS_STEPS.length
        ) {

          currentStep = 0;

          resetProgress();
        }

        activateStep(
          currentStep
        );

      },
      2500
    );
}


function stopProgressAnimation() {

  if (
    currentProgressInterval
  ) {

    clearInterval(
      currentProgressInterval
    );

    currentProgressInterval =
      null;
  }
}


function completeProgress() {

  stopProgressAnimation();

  PROGRESS_STEPS.forEach(
    (
      stepId
    ) => {

      const step =
        document.getElementById(
          stepId
        );

      step.classList.remove(
        "active"
      );

      step.classList.add(
        "completed"
      );

    }
  );
}


function hideProgress() {

  stopProgressAnimation();

  document
    .getElementById(
      "runningSection"
    )
    .classList.add(
      "hidden"
    );
}


// ==========================================
// GUARDRAIL
// ==========================================

function showGuardrail(data) {

  const section =
    document.getElementById(
      "guardrailSection"
    );

  const badge =
    document.getElementById(
      "guardrailBadge"
    );

  const reason =
    document.getElementById(
      "guardrailReason"
    );


  const allowed =
    data.guardrail_allowed !== false;


  if (allowed) {

    badge.textContent =
      "✓ Passed";

    badge.className =
      "guardrail-badge passed";

  } else {

    badge.textContent =
      "Blocked";

    badge.className =
      "guardrail-badge blocked";
  }


  reason.textContent =
    data.guardrail_reason ||
    "Input validation completed.";


  section.classList.remove(
    "hidden"
  );
}


// ==========================================
// FINDINGS
// ==========================================

function showFindings(findings) {

  const section =
    document.getElementById(
      "findingsSection"
    );

  const container =
    document.getElementById(
      "findingsContainer"
    );


  container.innerHTML = "";


  if (
    !findings ||
    findings.length === 0
  ) {

    return;
  }


  findings.forEach(
    (
      finding,
      index
    ) => {

      const card =
        document.createElement(
          "div"
        );

      card.className =
        "item-card";


      const title =
        finding.title ||
        finding.claim ||
        `Finding ${index + 1}`;


      const content =
        finding.content ||
        finding.summary ||
        finding.finding ||
        finding.description ||
        "";


      const source =
        finding.source ||
        finding.url ||
        "";


      card.innerHTML = `

        <div class="item-card-header">

          <span class="item-number">
            ${index + 1}
          </span>

          <h3>
            ${escapeHtml(title)}
          </h3>

        </div>

        <p>
          ${escapeHtml(content)}
        </p>

        ${
          source
            ? `
              <a
                href="${escapeHtml(source)}"
                target="_blank"
                rel="noopener noreferrer"
              >
                View Source →
              </a>
            `
            : ""
        }

      `;


      container.appendChild(
        card
      );

    }
  );


  section.classList.remove(
    "hidden"
  );
}


// ==========================================
// RISKS
// ==========================================

function showRisks(risks) {

  const section =
    document.getElementById(
      "risksSection"
    );

  const container =
    document.getElementById(
      "risksContainer"
    );


  container.innerHTML = "";


  if (
    !risks ||
    risks.length === 0
  ) {

    return;
  }


  risks.forEach(
    (
      risk,
      index
    ) => {

      const card =
        document.createElement(
          "div"
        );

      card.className =
        "item-card risk-card";


      const title =
        risk.title ||
        risk.risk ||
        `Risk ${index + 1}`;


      const description =
        risk.description ||
        risk.content ||
        risk.reason ||
        "";


      const severity =
        (
          risk.severity ||
          "unknown"
        ).toLowerCase();


      card.innerHTML = `

        <div class="item-card-header">

          <span class="severity ${severity}">
            ${escapeHtml(severity)}
          </span>

          <h3>
            ${escapeHtml(title)}
          </h3>

        </div>

        <p>
          ${escapeHtml(description)}
        </p>

      `;


      container.appendChild(
        card
      );

    }
  );


  section.classList.remove(
    "hidden"
  );
}


// ==========================================
// VERIFICATIONS
// ==========================================

function showVerifications(
  verifications
) {

  const section =
    document.getElementById(
      "factCheckSection"
    );

  const container =
    document.getElementById(
      "verificationsContainer"
    );


  container.innerHTML = "";


  if (
    !verifications ||
    verifications.length === 0
  ) {

    return;
  }


  verifications.forEach(
    (
      verification,
      index
    ) => {

      const card =
        document.createElement(
          "div"
        );

      card.className =
        "item-card";


      const claim =
        verification.claim ||
        verification.title ||
        `Claim ${index + 1}`;


      const explanation =
        verification.reason ||
        verification.explanation ||
        verification.content ||
        "";


      const status =
        (
          verification.status ||
          "unverified"
        ).toLowerCase();


      card.innerHTML = `

        <div class="item-card-header">

          <span class="verification-status ${status}">
            ${escapeHtml(status)}
          </span>

        </div>

        <h3>
          ${escapeHtml(claim)}
        </h3>

        <p>
          ${escapeHtml(explanation)}
        </p>

      `;


      container.appendChild(
        card
      );

    }
  );


  section.classList.remove(
    "hidden"
  );
}


// ==========================================
// HUMAN REVIEW
// ==========================================

function showHumanReview(data) {

  waitingForReview = true;


  const section =
    document.getElementById(
      "humanReviewSection"
    );


  const message =
    document.getElementById(
      "humanReviewMessage"
    );


  const container =
    document.getElementById(
      "reviewItemsContainer"
    );


  message.textContent =
    data.human_review_message ||
    "Please review the research results.";


  container.innerHTML = "";


  (
    data.human_review_items ||
    []
  ).forEach(
    (
      item,
      index
    ) => {

      const card =
        document.createElement(
          "div"
        );

      card.className =
        "review-item";


      const status =
        item.status ||
        "review";


      const claim =
        item.claim ||
        item.title ||
        `Review Item ${index + 1}`;


      const explanation =
        item.reason ||
        item.explanation ||
        item.content ||
        "";


      card.innerHTML = `

        <span class="verification-status ${status}">
          ${escapeHtml(status)}
        </span>

        <h3>
          ${escapeHtml(claim)}
        </h3>

        <p>
          ${escapeHtml(explanation)}
        </p>

      `;


      container.appendChild(
        card
      );

    }
  );


  section.classList.remove(
    "hidden"
  );


  section.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}


function hideHumanReview() {

  waitingForReview = false;

  document
    .getElementById(
      "humanReviewSection"
    )
    .classList.add(
      "hidden"
    );
}


// ==========================================
// FINAL REPORT
// ==========================================

function showFinalReport(data) {

  const section =
    document.getElementById(
      "reportSection"
    );

  const report =
    document.getElementById(
      "finalReport"
    );

  const threadInfo =
    document.getElementById(
      "threadInfo"
    );


  const reportText =
    data.final_report ||
    data.last_message ||
    "";


  renderMarkdown(
    report,
    reportText
  );


  threadInfo.textContent =
    `Thread ID: ${
      data.thread_id || "-"
    }`;


  section.classList.remove(
    "hidden"
  );


  section.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}


// ==========================================
// DISPLAY RESULT
// ==========================================

function displayResearchResult(data) {

  if (
    data.thread_id
  ) {

    currentThreadId =
      data.thread_id;

    localStorage.setItem(
      "research_thread_id",
      currentThreadId
    );
  }


  showGuardrail(
    data
  );


  if (
    data.guardrail_allowed === false
  ) {

    return;
  }


  showFindings(
    data.research_findings
  );


  showRisks(
    data.risks
  );


  showVerifications(
    data.verifications
  );


  if (
    data.requires_human_review
  ) {

    showHumanReview(
      data
    );

  } else {

    hideHumanReview();

    showFinalReport(
      data
    );
  }
}


// ==========================================
// START RESEARCH
// ==========================================

async function startResearch() {

  hideError();


  if (
    waitingForReview
  ) {

    showError(
      "Please complete the current human review before starting new research."
    );

    return;
  }


  const input =
    document.getElementById(
      "queryInput"
    );


  const message =
    input.value.trim();


  if (
    !message
  ) {

    showError(
      "Please enter a research question first."
    );

    input.focus();

    return;
  }


  setLoading(
    true
  );


  setStatus(
    "Researching...",
    "loading"
  );


  startProgressAnimation();


  try {

    const response =
      await fetch(
        "/api/research",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify(
              {
                message: message,

                thread_id:
                  currentThreadId
              }
            )
        }
      );


    const data =
      await response.json();


    if (
      !response.ok ||
      !data.success
    ) {

      throw new Error(
        data.error ||
        "Something went wrong during research."
      );
    }


    completeProgress();


    setTimeout(
      () => {

        hideProgress();

        displayResearchResult(
          data
        );

      },
      800
    );


    setStatus(
      data.requires_human_review
        ? "Review Required"
        : "Completed",
      data.requires_human_review
        ? "warning"
        : "success"
    );

  } catch (error) {

    hideProgress();


    setStatus(
      "Error",
      "error"
    );


    showError(
      error.message
    );

  } finally {

    setLoading(
      false
    );
  }
}


// ==========================================
// SUBMIT HUMAN REVIEW
// ==========================================

async function submitReview(
  decision
) {

  hideError();


  if (
    !currentThreadId
  ) {

    showError(
      "No active research thread found."
    );

    return;
  }


  const feedbackInput =
    document.getElementById(
      "feedbackInput"
    );


  const feedback =
    feedbackInput.value.trim();


  if (
    decision === "reject" &&
    !feedback
  ) {

    showError(
      "Please provide feedback before rejecting."
    );

    feedbackInput.focus();

    return;
  }


  setStatus(
    "Processing review...",
    "loading"
  );


  startProgressAnimation();


  disableReviewButtons(
    true
  );


  try {

    const response =
      await fetch(
        "/api/research/review",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify(
              {
                thread_id:
                  currentThreadId,

                decision:
                  decision,

                feedback:
                  feedback
              }
            )
        }
      );


    const data =
      await response.json();


    if (
      !response.ok ||
      !data.success
    ) {

      throw new Error(
        data.error ||
        "Could not resume the research workflow."
      );
    }


    completeProgress();


    setTimeout(
      () => {

        hideProgress();

        displayResearchResult(
          data
        );

      },
      800
    );


    setStatus(
      data.requires_human_review
        ? "Review Required"
        : "Completed",

      data.requires_human_review
        ? "warning"
        : "success"
    );

  } catch (error) {

    hideProgress();


    setStatus(
      "Error",
      "error"
    );


    showError(
      error.message
    );

  } finally {

    disableReviewButtons(
      false
    );
  }
}


// ==========================================
// REVIEW BUTTONS
// ==========================================

function disableReviewButtons(
  disabled
) {

  const buttons = [

    "approveButton",

    "moreResearchButton",

    "rejectButton"

  ];


  buttons.forEach(
    (
      buttonId
    ) => {

      const button =
        document.getElementById(
          buttonId
        );

      if (
        button
      ) {

        button.disabled =
          disabled;
      }

    }
  );
}


// ==========================================
// COPY REPORT
// ==========================================

function copyReport() {

  const report =
    document.getElementById(
      "finalReport"
    );


  const text =
    report.innerText;


  if (
    !text
  ) {

    return;
  }


  navigator.clipboard
    .writeText(
      text
    )

    .then(
      () => {

        const button =
          document.querySelector(
            ".copy-btn"
          );


        const oldText =
          button.textContent;


        button.textContent =
          "Copied ✓";


        setTimeout(
          () => {

            button.textContent =
              oldText;

          },
          1500
        );

      }
    )

    .catch(
      () => {

        showError(
          "Could not copy the report."
        );

      }
    );
}


// ==========================================
// ESCAPE HTML
// ==========================================

function escapeHtml(value) {

  if (
    value === null ||
    value === undefined
  ) {

    return "";
  }


  return String(value)

    .replace(
      /&/g,
      "&amp;"
    )

    .replace(
      /</g,
      "&lt;"
    )

    .replace(
      />/g,
      "&gt;"
    )

    .replace(
      /"/g,
      "&quot;"
    )

    .replace(
      /'/g,
      "&#039;"
    );
}


// ==========================================
// KEYBOARD SHORTCUT
// ==========================================

document.addEventListener(
  "keydown",
  function(event) {

    if (
      event.ctrlKey &&
      event.key === "Enter"
    ) {

      startResearch();

    }

  }
);
