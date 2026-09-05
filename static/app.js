let currentThreadId = null;
let currentProgressInterval = null;
let waitingForReview = false;
let isSubmittingReview = false;

// Only the explicit backend "human_review_required"
// event is allowed to open the Human Review UI.
let allowHumanReviewDisplay = false;


// ==========================================
// PROMPTS
// ==========================================

function setPrompt(text) {

  const input =
    document.getElementById("queryInput");

  if (!input) {
    return;
  }

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

  if (statusText) {
    statusText.textContent = text;
  }

  if (badge) {
    badge.className =
      `status-pill ${type}`;
  }
}


// ==========================================
// LOADING
// ==========================================

function setLoading(isLoading) {

  const button =
    document.getElementById("researchButton");

  const input =
    document.getElementById("queryInput");

  const buttonText =
    document.getElementById("buttonText");

  const buttonLoader =
    document.getElementById("buttonLoader");


  if (button) {
    button.disabled = isLoading;
  }

  if (input) {
    input.disabled = isLoading;
  }


  if (isLoading) {

    if (buttonText) {
      buttonText.classList.add("hidden");
    }

    if (buttonLoader) {
      buttonLoader.classList.remove("hidden");
    }

  } else {

    if (buttonText) {
      buttonText.classList.remove("hidden");
    }

    if (buttonLoader) {
      buttonLoader.classList.add("hidden");
    }
  }
}


// ==========================================
// ERROR
// ==========================================

function showError(message) {

  const errorBox =
    document.getElementById("errorBox");

  if (!errorBox) {
    return;
  }

  errorBox.textContent = message;

  errorBox.classList.remove("hidden");

  errorBox.scrollIntoView({
    behavior: "smooth",
    block: "center"
  });
}


function hideError() {

  const errorBox =
    document.getElementById("errorBox");

  if (!errorBox) {
    return;
  }

  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}


// ==========================================
// MARKDOWN
// ==========================================

function renderMarkdown(element, markdown) {

  if (!element) {
    return;
  }

  let text = "";


  if (markdown == null) {

    text = "";

  } else if (
    typeof markdown === "string"
  ) {

    text = markdown;

  } else if (
    Array.isArray(markdown)
  ) {

    text = markdown
      .map(item => {

        if (typeof item === "string") {
          return item;
        }

        if (
          item &&
          typeof item.text === "string"
        ) {
          return item.text;
        }

        if (
          item &&
          typeof item.content === "string"
        ) {
          return item.content;
        }

        return "";
      })
      .filter(Boolean)
      .join("\n\n");

  } else if (
    typeof markdown === "object"
  ) {

    if (
      typeof markdown.text === "string"
    ) {

      text = markdown.text;

    } else if (
      typeof markdown.content === "string"
    ) {

      text = markdown.content;

    } else {

      text = JSON.stringify(markdown);
    }

  } else {

    text = String(markdown);
  }


  if (
    typeof marked !== "undefined"
  ) {

    element.innerHTML =
      marked.parse(text);

  } else {

    element.innerText = text;
  }
}


// ==========================================
// PROGRESS
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
    stepId => {

      const step =
        document.getElementById(stepId);

      if (!step) {
        return;
      }

      step.classList.remove("active");
      step.classList.remove("completed");
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


  if (!runningSection) {
    return;
  }


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


        if (!step) {
          return;
        }


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


    if (activeStep) {
      activeStep.classList.add(
        "active"
      );
    }
  }


  activateStep(currentStep);


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

    currentProgressInterval = null;
  }
}


function completeProgress() {

  stopProgressAnimation();


  PROGRESS_STEPS.forEach(
    stepId => {

      const step =
        document.getElementById(
          stepId
        );


      if (!step) {
        return;
      }


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


  const runningSection =
    document.getElementById(
      "runningSection"
    );


  if (runningSection) {

    runningSection.classList.add(
      "hidden"
    );
  }
}


// ==========================================
// CLEAR PREVIOUS RESULTS
// ==========================================

function clearPreviousResults() {

  const sections = [

    "guardrailSection",

    "findingsSection",

    "risksSection",

    "factCheckSection",

    "humanReviewSection",

    "reportSection",

    "errorBox"

  ];


  sections.forEach(
    sectionId => {

      const section =
        document.getElementById(
          sectionId
        );


      if (section) {

        section.classList.add(
          "hidden"
        );
      }
    }
  );


  const containers = [

    "findingsContainer",

    "risksContainer",

    "verificationsContainer",

    "reviewItemsContainer",

    "finalReport"

  ];


  containers.forEach(
    containerId => {

      const element =
        document.getElementById(
          containerId
        );


      if (element) {
        element.innerHTML = "";
      }
    }
  );


  const humanReviewMessage =
    document.getElementById(
      "humanReviewMessage"
    );


  if (humanReviewMessage) {
    humanReviewMessage.textContent = "";
  }


  const guardrailReason =
    document.getElementById(
      "guardrailReason"
    );


  if (guardrailReason) {
    guardrailReason.textContent = "";
  }


  const threadInfo =
    document.getElementById(
      "threadInfo"
    );


  if (threadInfo) {

    threadInfo.textContent =
      "Thread ID: -";
  }


  const feedbackInput =
    document.getElementById(
      "feedbackInput"
    );


  if (feedbackInput) {
    feedbackInput.value = "";
  }


  waitingForReview = false;
  isSubmittingReview = false;
  allowHumanReviewDisplay = false;


  disableReviewButtons(true);
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


  if (!section) {
    return;
  }


  const allowed =
    data.guardrail_allowed !== false;


  if (badge) {

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
  }


  if (reason) {

    reason.textContent =
      data.guardrail_reason ||
      "Input validation completed.";
  }


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


  if (!section || !container) {
    return;
  }


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


  if (!section || !container) {
    return;
  }


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

          <span class="severity ${escapeHtml(severity)}">
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


  // This is important:
  // New Risk Agent results are allowed
  // to make the Risks section visible again.
  section.classList.remove(
    "hidden"
  );
}


// ==========================================
// FACT CHECK
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


  if (!section || !container) {
    return;
  }


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

          <span class="verification-status ${escapeHtml(status)}">
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


  // This is important:
  // New Fact Checker results are allowed
  // to make the Fact Check section visible.
  section.classList.remove(
    "hidden"
  );
}


// ==========================================
// HUMAN REVIEW
// ==========================================

function showHumanReview(data) {

  console.log(
    "🔎 showHumanReview() called"
  );


  // ==========================================
  // SAFETY CHECK
  // ==========================================
  //
  // NEVER display HITL unless the backend
  // explicitly sent human_review_required.
  //

  if (!allowHumanReviewDisplay) {

    console.log(
      "🚫 HITL display blocked — no explicit human_review_required event."
    );

    return;
  }


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


  if (!section) {
    return;
  }


  // ==========================================
  // SAVE THREAD
  // ==========================================

  if (data.thread_id) {

    currentThreadId =
      data.thread_id;


    localStorage.setItem(
      "research_thread_id",
      currentThreadId
    );


    console.log(
      "💾 Human review thread:",
      currentThreadId
    );
  }


  // ==========================================
  // MESSAGE
  // ==========================================

  if (message) {

    message.textContent =
      data.human_review_message ||
      "Please review the research results.";
  }


  // ==========================================
  // ITEMS
  // ==========================================

  if (container) {

    container.innerHTML = "";


    const items =
      data.human_review_items || [];


    items.forEach(
      item => {

        const card =
          document.createElement(
            "div"
          );


        card.className =
          "item-card";


        card.textContent =
          typeof item === "string"
            ? item
            : (
                item.content ||
                item.claim ||
                JSON.stringify(item)
              );


        container.appendChild(
          card
        );
      }
    );
  }


  // ==========================================
  // SHOW HITL
  // ==========================================

  section.classList.remove(
    "hidden"
  );


  waitingForReview = true;
  isSubmittingReview = false;


  disableReviewButtons(false);


  setStatus(
    "Waiting for human review",
    "warning"
  );


  section.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });


  console.log(
    "👤 Human Review UI displayed"
  );
}


// ==========================================
// HIDE HUMAN REVIEW
// ==========================================

function hideHumanReview() {

  const section =
    document.getElementById(
      "humanReviewSection"
    );


  if (section) {

    section.classList.add(
      "hidden"
    );
  }


  const container =
    document.getElementById(
      "reviewItemsContainer"
    );


  if (container) {
    container.innerHTML = "";
  }


  const message =
    document.getElementById(
      "humanReviewMessage"
    );


  if (message) {
    message.textContent = "";
  }


  console.log(
    "🙈 Human Review UI hidden"
  );
}


// ==========================================
// HIDE EVERYTHING BELOW FINDINGS
// ==========================================

function hideResultsAfterResearchFindings() {

  console.log(
    "🧹 Clearing old downstream results..."
  );


  // ==========================================
  // IMPORTANT
  // ==========================================
  //
  // A previous HITL must not be allowed
  // to reappear during the resumed workflow.
  //

  allowHumanReviewDisplay = false;


  // ==========================================
  // HIDE SECTIONS
  // ==========================================

  const sectionsToHide = [

    "risksSection",

    "factCheckSection",

    "humanReviewSection",

    "reportSection"

  ];


  sectionsToHide.forEach(
    sectionId => {

      const section =
        document.getElementById(
          sectionId
        );


      if (section) {

        section.classList.add(
          "hidden"
        );


        console.log(
          `🙈 Hidden: ${sectionId}`
        );
      }
    }
  );


  // ==========================================
  // CLEAR OLD RISKS
  // ==========================================

  const risksContainer =
    document.getElementById(
      "risksContainer"
    );


  if (risksContainer) {
    risksContainer.innerHTML = "";
  }


  // ==========================================
  // CLEAR OLD FACT CHECK
  // ==========================================

  const verificationsContainer =
    document.getElementById(
      "verificationsContainer"
    );


  if (verificationsContainer) {
    verificationsContainer.innerHTML = "";
  }


  // ==========================================
  // CLEAR OLD HITL
  // ==========================================

  const reviewItemsContainer =
    document.getElementById(
      "reviewItemsContainer"
    );


  if (reviewItemsContainer) {
    reviewItemsContainer.innerHTML = "";
  }


  const humanReviewMessage =
    document.getElementById(
      "humanReviewMessage"
    );


  if (humanReviewMessage) {
    humanReviewMessage.textContent = "";
  }


  // ==========================================
  // CLEAR OLD REPORT
  // ==========================================

  const finalReport =
    document.getElementById(
      "finalReport"
    );


  if (finalReport) {
    finalReport.innerHTML = "";
  }


  console.log(
    "🧹 Old Risks, Fact Check, HITL and Report cleared"
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


  if (!section || !report) {
    return;
  }


  let reportText =
    data.final_report ??
    data.last_message ??
    "";


  // ==========================================
  // ARRAY
  // ==========================================

  if (
    Array.isArray(reportText)
  ) {

    reportText =
      reportText
        .map(item => {

          if (
            typeof item === "string"
          ) {
            return item;
          }

          if (
            item &&
            typeof item.text === "string"
          ) {
            return item.text;
          }

          if (
            item &&
            typeof item.content === "string"
          ) {
            return item.content;
          }

          return "";

        })
        .filter(Boolean)
        .join("\n\n");
  }


  // ==========================================
  // OBJECT
  // ==========================================

  if (
    reportText &&
    typeof reportText === "object"
  ) {

    if (
      typeof reportText.text === "string"
    ) {

      reportText =
        reportText.text;

    } else if (
      typeof reportText.content === "string"
    ) {

      reportText =
        reportText.content;

    } else {

      reportText =
        JSON.stringify(reportText);
    }
  }


  reportText =
    String(
      reportText || ""
    );


  // ==========================================
  // DISPLAY
  // ==========================================

  renderMarkdown(
    report,
    reportText
  );


  // ==========================================
  // THREAD INFO
  // ==========================================

  if (threadInfo) {

    threadInfo.textContent =
      `Thread ID: ${
        data.thread_id ||
        currentThreadId ||
        "-"
      }`;
  }


  section.classList.remove(
    "hidden"
  );


  section.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}


// ==========================================
// DISPLAY COMPLETE RESULT
// ==========================================

function displayResearchResult(data) {

  if (data.thread_id) {

    currentThreadId =
      data.thread_id;


    localStorage.setItem(
      "research_thread_id",
      currentThreadId
    );
  }


  showGuardrail(data);


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

    allowHumanReviewDisplay = true;

    showHumanReview(
      data
    );

  } else {

    allowHumanReviewDisplay = false;

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


  // ==========================================
  // DON'T START WHILE WAITING FOR HITL
  // ==========================================

  if (waitingForReview) {

    showError(
      "Please complete the current human review before starting new research."
    );

    return;
  }


  const input =
    document.getElementById(
      "queryInput"
    );


  if (!input) {

    showError(
      "Research input was not found."
    );

    return;
  }


  const message =
    input.value.trim();


  // ==========================================
  // VALIDATE INPUT
  // ==========================================

  if (!message) {

    showError(
      "Please enter a research question first."
    );

    input.focus();

    return;
  }


  // ==========================================
  // NEW RESEARCH = NEW THREAD
  // ==========================================

  clearCurrentThread();


  clearPreviousResults();


  setLoading(true);


  setStatus(
    "Starting research...",
    "loading"
  );


  startAgentProgress();


  try {

    const response =
      await fetch(
        "/api/research/stream",
        {

          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body:
            JSON.stringify({

              message:
                message,

              // Backend creates a new thread
              thread_id:
                null

            })
        }
      );


    if (!response.ok) {

      let errorMessage =
        "Could not start research.";


      try {

        const error =
          await response.json();


        errorMessage =
          error.error ||
          errorMessage;

      } catch (_) {
        // Ignore JSON parsing error
      }


      throw new Error(
        errorMessage
      );
    }


    if (!response.body) {

      throw new Error(
        "The server did not return a streaming response."
      );
    }


    const reader =
      response.body.getReader();


    const decoder =
      new TextDecoder();


    let buffer = "";


    while (true) {

      const {
        value,
        done
      } =
        await reader.read();


      if (done) {
        break;
      }


      buffer +=
        decoder.decode(
          value,
          {
            stream: true
          }
        );


      const events =
        buffer.split("\n\n");


      buffer =
        events.pop();


      for (
        const eventText of events
      ) {

        if (
          !eventText.startsWith("data:")
        ) {
          continue;
        }


        const jsonText =
          eventText
            .replace(
              /^data:\s*/,
              ""
            )
            .trim();


        if (!jsonText) {
          continue;
        }


        try {

          const event =
            JSON.parse(
              jsonText
            );


          console.log(
            "📡 Research SSE event:",
            event
          );


          handleStreamEvent(
            event
          );

        } catch (parseError) {

          console.error(
            "❌ Could not parse research SSE event:",
            jsonText,
            parseError
          );
        }
      }
    }


    console.log(
      "🏁 Research stream finished"
    );


  } catch (error) {

    console.error(
      "❌ Research error:",
      error
    );


    hideProgress();


    setStatus(
      "Error",
      "error"
    );


    showError(
      error.message
    );


  } finally {

    setLoading(false);
  }
}


// ==========================================
// SUBMIT HUMAN REVIEW
// ==========================================

async function submitReview(
  decision
) {

  hideError();


  // ==========================================
  // PREVENT DOUBLE CLICK
  // ==========================================

  if (isSubmittingReview) {

    console.log(
      "⚠️ Review submission already in progress"
    );

    return;
  }


  // ==========================================
  // CHECK THREAD
  // ==========================================

  if (!currentThreadId) {

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
    feedbackInput
      ? feedbackInput.value.trim()
      : "";


  // ==========================================
  // VALIDATE REJECT
  // ==========================================

  if (
    decision === "reject" &&
    !feedback
  ) {

    showError(
      "Please provide feedback before rejecting."
    );


    if (feedbackInput) {
      feedbackInput.focus();
    }


    return;
  }


  // ==========================================
  // LOCK REVIEW
  // ==========================================

  isSubmittingReview = true;
  waitingForReview = false;

  // Prevent the old HITL from reopening.
  allowHumanReviewDisplay = false;


  disableReviewButtons(true);


  setLoading(true);


  setStatus(
    "Processing review...",
    "loading"
  );


  // ==========================================
  // HIDE OLD HITL
  // ==========================================

  hideHumanReview();


  // ==========================================
  // NEEDS MORE RESEARCH
  // ==========================================

  if (
    decision === "request_more_research"
  ) {

    hideResultsAfterResearchFindings();


    console.log(
      "🔄 Requesting more research for thread:",
      currentThreadId
    );
  }


  startAgentProgress();


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
            JSON.stringify({

              thread_id:
                currentThreadId,

              decision:
                decision,

              feedback:
                feedback

            })
        }
      );


    console.log(
      "📡 Review HTTP status:",
      response.status
    );


    if (!response.ok) {

      let errorMessage =
        "Could not resume the research workflow.";


      try {

        const error =
          await response.json();


        errorMessage =
          error.error ||
          errorMessage;

      } catch (_) {
        // Ignore JSON parsing error
      }


      throw new Error(
        errorMessage
      );
    }


    if (!response.body) {

      throw new Error(
        "The server did not return a streaming response."
      );
    }


    const reader =
      response.body.getReader();


    const decoder =
      new TextDecoder();


    let buffer = "";


    while (true) {

      const {
        value,
        done
      } =
        await reader.read();


      if (done) {

        console.log(
          "🏁 Review SSE stream closed"
        );

        break;
      }


      buffer +=
        decoder.decode(
          value,
          {
            stream: true
          }
        );


      const events =
        buffer.split("\n\n");


      buffer =
        events.pop();


      for (
        const rawEvent of events
      ) {

        if (
          !rawEvent.startsWith("data:")
        ) {
          continue;
        }


        const jsonText =
          rawEvent
            .replace(
              /^data:\s*/,
              ""
            )
            .trim();


        if (!jsonText) {
          continue;
        }


        try {

          const event =
            JSON.parse(
              jsonText
            );


          console.log(
            "📡 Review SSE event:",
            event
          );


          handleStreamEvent(
            event
          );

        } catch (parseError) {

          console.error(
            "❌ Failed to parse review SSE event:",
            jsonText,
            parseError
          );
        }
      }
    }


    console.log(
      "✅ Review stream finished"
    );


  } catch (error) {

    console.error(
      "❌ Review error:",
      error
    );


    hideProgress();


    setStatus(
      "Error",
      "error"
    );


    showError(
      error.message
    );


    // The request failed, so allow the
    // user to retry the current review.
    isSubmittingReview = false;
    waitingForReview = true;

    allowHumanReviewDisplay = true;


    showHumanReview({

      thread_id:
        currentThreadId,

      human_review_message:
        "The review request failed. Please try again."

    });


  } finally {

    setLoading(false);


    // IMPORTANT:
    //
    // Never enable review buttons here.
    //
    // If the backend requests another HITL,
    // showHumanReview() enables them.
    //
    // If the workflow completes, they remain disabled.
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
    buttonId => {

      const button =
        document.getElementById(
          buttonId
        );


      if (button) {

        button.disabled =
          disabled;
      }
    }
  );
}


// ==========================================
// HANDLE ALL SSE EVENTS
// ==========================================

function handleStreamEvent(event) {

  console.log(
    "📥 HANDLE EVENT:",
    event.type,
    "| agent:",
    event.agent,
    "| thread:",
    event.thread_id
  );


  // ==========================================
  // THREAD ID
  // ==========================================

  if (event.thread_id) {

    currentThreadId =
      event.thread_id;


    localStorage.setItem(
      "research_thread_id",
      currentThreadId
    );


    console.log(
      "🧵 Active research thread:",
      currentThreadId
    );
  }


  // ==========================================
  // AGENT STARTED
  // ==========================================

  if (
    event.type === "agent_started"
  ) {

    showRunningAgent(
      event.agent
    );

    return;
  }


  // ==========================================
  // AGENT UPDATE
  // ==========================================

  if (
    event.type === "agent_update"
  ) {

    handleAgentUpdate(
      event
    );

    return;
  }


  // ==========================================
  // HUMAN REVIEW REQUIRED
  // ==========================================

  if (
    event.type === "human_review_required"
  ) {

    console.log(
      "⏸️ NEW HUMAN REVIEW REQUIRED"
    );


    // ==========================================
    // THIS IS THE ONLY NORMAL EVENT THAT
    // ENABLES HUMAN REVIEW DISPLAY.
    // ==========================================

    allowHumanReviewDisplay = true;


    stopProgressAnimation();


    showHumanReview({

      human_review_message:
        event.human_review_message ||
        "Please review the research results.",

      human_review_items:
        event.human_review_items || [],

      thread_id:
        event.thread_id

    });


    setStatus(
      "Waiting for human review",
      "warning"
    );


    return;
  }


  // ==========================================
  // COMPLETE
  // ==========================================

  if (
    event.type === "complete"
  ) {

    const data =
      event.data || {};


    console.log(
      "🏁 WORKFLOW COMPLETE:",
      data
    );


    // ==========================================
    // SAVE THREAD
    // ==========================================

    if (data.thread_id) {

      currentThreadId =
        data.thread_id;


      localStorage.setItem(
        "research_thread_id",
        currentThreadId
      );


      console.log(
        "🧵 Completed thread:",
        currentThreadId
      );
    }


    // ==========================================
    // ANOTHER HITL REQUIRED
    // ==========================================

    if (
      data.requires_human_review
    ) {

      console.log(
        "⏸️ Complete event says another review is required"
      );


      allowHumanReviewDisplay = true;

      waitingForReview = true;
      isSubmittingReview = false;


      setStatus(
        "Waiting for human review",
        "warning"
      );


      showHumanReview(
        data
      );


      return;
    }


    // ==========================================
    // ACTUAL WORKFLOW COMPLETION
    // ==========================================

    console.log(
      "✅ Research workflow completely finished"
    );


    waitingForReview = false;
    isSubmittingReview = false;

    allowHumanReviewDisplay = false;


    // Review buttons stay disabled
    disableReviewButtons(true);


    completeProgress();


    setTimeout(
      () => {

        hideProgress();

        // Hide all intermediate results
        // before displaying the final report.
        showOnlyFinalReport();


        showFinalReport(
          data
        );


        setStatus(
          "Completed",
          "success"
        );


        console.log(
          "📄 Final report displayed"
        );

      },
      500
    );


    return;
  }


  // ==========================================
  // ERROR
  // ==========================================

  if (
    event.type === "error"
  ) {

    setStatus(
      "Error",
      "error"
    );


    showError(
      event.error ||
      "An unexpected error occurred."
    );


    return;
  }
}


// ==========================================
// HANDLE AGENT UPDATE
// ==========================================

function handleAgentUpdate(event) {

  if (
    event.type !== "agent_update"
  ) {
    return;
  }


  const agent =
    event.agent;


  const update =
    event.update || {};


  switch (agent) {


    // ========================================
    // INPUT GUARDRAIL
    // ========================================

    case "input_guardrail":

      updateProgressStep(
        "progress-guardrail"
      );


      showGuardrail({

        guardrail_allowed:
          update.input_guardrail_allowed,

        guardrail_reason:
          update.input_guardrail_reason

      });


      break;


    // ========================================
    // RESEARCH AGENT
    // ========================================

    case "research_agent":

      updateProgressStep(
        "progress-research"
      );


      if (
        update.research_findings
      ) {

        console.log(
          "🔬 New Research Findings received"
        );


        showFindings(
          update.research_findings
        );
      }


      break;


    // ========================================
    // RISK AGENT
    // ========================================

    case "risk_agent":

      updateProgressStep(
        "progress-risk"
      );


      if (
        update.risks
      ) {

        console.log(
          "⚠️ New Risk results received"
        );


        showRisks(
          update.risks
        );
      }


      break;


    // ========================================
    // FACT CHECKER
    // ========================================

    case "fact_checker_agent":

      updateProgressStep(
        "progress-fact"
      );


      if (
        update.verifications
      ) {

        console.log(
          "🔎 New Fact Check results received"
        );


        showVerifications(
          update.verifications
        );
      }


      break;


    // ========================================
    // REPORT GENERATOR
    // ========================================

    case "report_generator":

      updateProgressStep(
        "progress-report"
      );


      console.log(
        "📄 Report Generator finished/updated"
      );


      break;


    // ========================================
    // HUMAN REVIEW
    // ========================================

    case "human_review":

      /*
       * VERY IMPORTANT:
       *
       * Do NOT call showHumanReview() here.
       *
       * The human_review agent can start or
       * produce an update without the workflow
       * necessarily being ready for user input.
       *
       * The backend's explicit:
       *
       *     human_review_required
       *
       * event is what opens the HITL panel.
       */

      console.log(
        "ℹ️ Human Review agent update received — HITL UI remains hidden until human_review_required."
      );


      setStatus(
        "Preparing human review...",
        "loading"
      );


      break;
  }
}


// ==========================================
// PROGRESS STEP
// ==========================================

function updateProgressStep(
  activeStepId
) {

  const activeIndex =
    PROGRESS_STEPS.indexOf(
      activeStepId
    );


  if (
    activeIndex === -1
  ) {

    return;
  }


  PROGRESS_STEPS.forEach(
    (
      stepId,
      index
    ) => {

      const step =
        document.getElementById(
          stepId
        );


      if (!step) {
        return;
      }


      step.classList.remove(
        "active"
      );


      if (
        index < activeIndex
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
      activeStepId
    );


  if (activeStep) {

    activeStep.classList.add(
      "active"
    );
  }
}


// ==========================================
// START AGENT PROGRESS
// ==========================================

function startAgentProgress() {

  stopProgressAnimation();

  resetProgress();


  const runningSection =
    document.getElementById(
      "runningSection"
    );


  if (runningSection) {

    runningSection.classList.remove(
      "hidden"
    );
  }


  setStatus(
    "Starting research...",
    "loading"
  );
}


// ==========================================
// SHOW RUNNING AGENT
// ==========================================

function showRunningAgent(
  agent
) {

  const agentNames = {

    input_guardrail:
      "Input Guardrail",

    supervisor:
      "Supervisor",

    research_agent:
      "Research Agent",

    risk_agent:
      "Risk Agent",

    fact_checker_agent:
      "Fact Checker",

    human_review:
      "Human Review",

    report_generator:
      "Report Generator"

  };


  const progressSteps = {

    input_guardrail:
      "progress-guardrail",

    research_agent:
      "progress-research",

    risk_agent:
      "progress-risk",

    fact_checker_agent:
      "progress-fact",

    report_generator:
      "progress-report"

  };


  const name =
    agentNames[agent] || agent;


  // ==========================================
  // STATUS
  // ==========================================

  if (
    agent === "human_review"
  ) {

    setStatus(
      "Preparing human review...",
      "loading"
    );

  } else {

    setStatus(
      `Running: ${name}`,
      "loading"
    );
  }


  // ==========================================
  // PROGRESS
  // ==========================================

  const stepId =
    progressSteps[agent];


  if (stepId) {

    updateProgressStep(
      stepId
    );
  }


  console.log(
    `▶️ Agent started: ${name}`
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


  if (!report) {
    return;
  }


  const text =
    report.innerText;


  if (!text) {
    return;
  }


  navigator.clipboard
    .writeText(text)

    .then(
      () => {

        const button =
          document.querySelector(
            ".copy-btn"
          );


        if (!button) {
          return;
        }


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


// ==========================================
// THREAD MANAGEMENT
// ==========================================

function clearCurrentThread() {

  currentThreadId = null;


  localStorage.removeItem(
    "research_thread_id"
  );


  console.log(
    "🗑️ Current research thread cleared"
  );
}

function showOnlyFinalReport() {

  const sectionsToHide = [
    "guardrailSection",
    "findingsSection",
    "risksSection",
    "factCheckSection",
    "humanReviewSection"
  ];

  sectionsToHide.forEach(sectionId => {

    const section =
      document.getElementById(sectionId);

    if (section) {
      section.classList.add("hidden");
    }
  });

  console.log(
    "🙈 Intermediate results hidden — showing final report only"
  );
}