const bundleInput = document.querySelector("#bundle-json");
const bundleFile = document.querySelector("#bundle-file");
const reviewButton = document.querySelector("#review-button");
const loadSampleButton = document.querySelector("#load-sample-button");
const clearButton = document.querySelector("#clear-button");
const copyTemplateButton = document.querySelector("#copy-template-button");
const summary = document.querySelector("#support-summary");
const findingList = document.querySelector("#finding-list");
const replyTemplate = document.querySelector("#reply-template");
const output = document.querySelector("#support-output");

const sampleBundle = {
  schema_version: "gw2radar.account_debug_bundle.v1",
  client_state: {
    active_view: "connect",
    active_build_id_present: false,
    player_intent: "build_fit",
    report_history_count: 0,
  },
  key_status: { is_configured: true, masked_key: "1234...9abc" },
  permission_summary: {
    key_configured: true,
    limited_mode: false,
    missing_required_permissions: [],
    missing_optional_permissions: [],
  },
  sync_summary: {
    status: "succeeded",
    counts: { succeeded: 1, retry_scheduled: 0 },
    endpoint_progress: [],
  },
  diagnostic_summary: {
    summary_status: "ready",
    checks: [
      { check_id: "api_key_stored", status: "pass" },
      { check_id: "permissions_ready", status: "pass" },
      { check_id: "sync_job_visible", status: "pass" },
      { check_id: "private_snapshot_written", status: "pass" },
      { check_id: "synced_character_snapshot", status: "pass" },
      { check_id: "build_fit_bridge_ready", status: "pass" },
    ],
    next_actions: [],
  },
  snapshot_summary: {
    private_player_state_count: 5,
    synced_character_snapshot_count: 1,
    manual_snapshot_count: 0,
    synced_gear_count: 4,
  },
  redaction_policy: ["Raw API keys are excluded."],
};

function setReviewState(review) {
  output.textContent = JSON.stringify(review, null, 2);
  summary.textContent = `${review.overall_status}: ${review.summary}`;
  summary.classList.toggle("ready", review.overall_status === "ready");
  findingList.innerHTML = "";
  const findings = Array.isArray(review.findings) ? review.findings : [];
  if (!findings.length) {
    const empty = document.createElement("div");
    empty.className = "support-finding info";
    empty.textContent = "No findings. The player can continue normal flow verification.";
    findingList.appendChild(empty);
  }
  for (const finding of findings) {
    const item = document.createElement("article");
    item.className = `support-finding ${finding.severity || "info"}`;
    const title = document.createElement("strong");
    title.textContent = finding.title || finding.finding_id;
    const message = document.createElement("p");
    message.textContent = finding.player_message || "";
    const action = document.createElement("p");
    action.textContent = `Action: ${finding.recommended_action || "Manual review required."}`;
    const evidence = document.createElement("code");
    evidence.textContent = (finding.evidence_refs || []).join(", ") || "no evidence path";
    item.append(title, message, action, evidence);
    findingList.appendChild(item);
  }
  replyTemplate.value = buildReplyTemplate(review);
}

function buildReplyTemplate(review) {
  const firstFinding = Array.isArray(review.findings) ? review.findings[0] : null;
  if (!firstFinding) {
    return [
      "Your debug bundle looks healthy on the backend side.",
      "Please open Build Fit, select or import a build, load the synced character snapshot, and run the fit check again.",
      "You do not need to send your raw GW2 API key.",
    ].join("\n");
  }
  return [
    `I reviewed your GW2Radar debug bundle. Current status: ${review.overall_status}.`,
    firstFinding.player_message,
    `Next step: ${firstFinding.recommended_action}`,
    "Please do not send your raw GW2 API key or private account payloads.",
  ].join("\n");
}

async function reviewBundle() {
  let bundle;
  try {
    bundle = JSON.parse(bundleInput.value || "{}");
  } catch (error) {
    summary.textContent = `Invalid JSON: ${error.message}`;
    output.textContent = "{}";
    findingList.innerHTML = "";
    replyTemplate.value = "The uploaded debug bundle is not valid JSON. Please export a fresh bundle and try again.";
    return;
  }
  const response = await fetch("/account/debug-bundle/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  });
  const review = await response.json();
  setReviewState(review);
}

bundleFile?.addEventListener("change", async () => {
  const file = bundleFile.files?.[0];
  if (!file) {
    return;
  }
  bundleInput.value = await file.text();
});

reviewButton?.addEventListener("click", reviewBundle);

loadSampleButton?.addEventListener("click", () => {
  bundleInput.value = JSON.stringify(sampleBundle, null, 2);
});

clearButton?.addEventListener("click", () => {
  bundleInput.value = "";
  summary.textContent = "No bundle reviewed yet.";
  findingList.innerHTML = "";
  replyTemplate.value = "";
  output.textContent = "{}";
});

copyTemplateButton?.addEventListener("click", async () => {
  if (!replyTemplate.value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(replyTemplate.value);
    summary.textContent = "Reply template copied. Keep the no-secret boundary in your response.";
  } catch {
    summary.textContent = "Copy failed. Select the reply template manually.";
  }
});
