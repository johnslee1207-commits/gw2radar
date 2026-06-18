const bundleInput = document.querySelector("#bundle-json");
const bundleFile = document.querySelector("#bundle-file");
const reviewButton = document.querySelector("#review-button");
const loadSampleButton = document.querySelector("#load-sample-button");
const clearButton = document.querySelector("#clear-button");
const copyTemplateButton = document.querySelector("#copy-template-button");
const saveAuditButton = document.querySelector("#save-audit-button");
const refreshAuditButton = document.querySelector("#refresh-audit-button");
const exportAuditButton = document.querySelector("#export-audit-button");
const refreshMetricsButton = document.querySelector("#refresh-metrics-button");
const refreshPlaybookButton = document.querySelector("#refresh-playbook-button");
const refreshBacklogButton = document.querySelector("#refresh-backlog-button");
const exportBacklogMdButton = document.querySelector("#export-backlog-md-button");
const exportBacklogCsvButton = document.querySelector("#export-backlog-csv-button");
const summary = document.querySelector("#support-summary");
const findingList = document.querySelector("#finding-list");
const replyTemplate = document.querySelector("#reply-template");
const reviewerName = document.querySelector("#reviewer-name");
const auditList = document.querySelector("#audit-list");
const auditStatusFilter = document.querySelector("#audit-status-filter");
const auditSeverityFilter = document.querySelector("#audit-severity-filter");
const auditReviewerFilter = document.querySelector("#audit-reviewer-filter");
const metricsSummary = document.querySelector("#metrics-summary");
const metricsStatusList = document.querySelector("#metrics-status-list");
const metricsSeverityList = document.querySelector("#metrics-severity-list");
const metricsBlockerList = document.querySelector("#metrics-blocker-list");
const playbookSummary = document.querySelector("#playbook-summary");
const playbookList = document.querySelector("#playbook-list");
const backlogSummary = document.querySelector("#backlog-summary");
const backlogList = document.querySelector("#backlog-list");
const output = document.querySelector("#support-output");
let lastBundle = null;
let lastReview = null;

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
  lastReview = review;
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
    lastBundle = null;
    lastReview = null;
    return;
  }
  lastBundle = bundle;
  const response = await fetch("/account/debug-bundle/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  });
  const review = await response.json();
  setReviewState(review);
}

async function saveAuditRecord() {
  if (!lastBundle || !lastReview) {
    summary.textContent = "Review a bundle before saving an audit record.";
    return;
  }
  const response = await fetch("/account/debug-bundle/review/audit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      bundle: lastBundle,
      reviewer: reviewerName?.value || "support",
      reply_template: replyTemplate.value,
      source: "support_workbench",
    }),
  });
  const payload = await response.json();
  summary.textContent = `Audit saved: ${payload.audit_record?.case_id || "unknown case"}. Raw bundle was not stored.`;
  output.textContent = JSON.stringify(payload, null, 2);
  await refreshAuditRecords();
}

async function refreshAuditRecords() {
  const response = await fetch(`/account/debug-bundle/review/audit?${auditQueryString()}`);
  const payload = await response.json();
  renderAuditRecords(payload.records || []);
  await refreshAuditMetrics();
  await refreshPlaybook();
  await refreshBacklog();
}

function auditQueryString(format = "json") {
  const params = new URLSearchParams();
  params.set("limit", "10");
  params.set("format", format);
  if (auditStatusFilter?.value) {
    params.set("status", auditStatusFilter.value.trim());
  }
  if (auditSeverityFilter?.value) {
    params.set("severity", auditSeverityFilter.value);
  }
  if (auditReviewerFilter?.value) {
    params.set("reviewer", auditReviewerFilter.value.trim());
  }
  return params.toString();
}

function exportAuditCsv() {
  window.location.href = `/account/debug-bundle/review/audit?${auditQueryString("csv")}`;
}

async function refreshAuditMetrics() {
  const response = await fetch(`/account/debug-bundle/review/audit/metrics?${auditQueryString()}`);
  const metrics = await response.json();
  renderAuditMetrics(metrics);
}

async function refreshPlaybook() {
  const response = await fetch(`/account/debug-bundle/review/audit/playbook?${auditQueryString()}`);
  const playbook = await response.json();
  renderPlaybook(playbook);
}

async function refreshBacklog() {
  const response = await fetch(`/account/debug-bundle/review/audit/backlog?${auditQueryString()}`);
  const backlog = await response.json();
  renderBacklog(backlog);
}

function renderAuditMetrics(metrics) {
  metricsSummary.textContent = `${metrics.total_records || 0} records. ${metrics.trend_summary || "No summary available."}`;
  renderMetricList(metricsStatusList, metrics.status_counts || []);
  renderMetricList(metricsSeverityList, metrics.severity_counts || []);
  renderMetricList(metricsBlockerList, metrics.top_blockers || []);
}

function renderMetricList(target, rows) {
  target.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("li");
    empty.textContent = "None";
    target.appendChild(empty);
    return;
  }
  for (const row of rows) {
    const item = document.createElement("li");
    item.textContent = `${row.key}: ${row.count}`;
    target.appendChild(item);
  }
}

function renderPlaybook(playbook) {
  playbookSummary.textContent = playbook.summary || "No playbook summary available.";
  playbookList.innerHTML = "";
  const plays = Array.isArray(playbook.plays) ? playbook.plays : [];
  if (!plays.length) {
    playbookList.textContent = "No mapped remediation play is available for the current filters.";
    return;
  }
  for (const play of plays) {
    const item = document.createElement("article");
    item.className = "support-playbook-item";
    const title = document.createElement("strong");
    title.textContent = `${play.priority || "P2"} · ${play.title || play.blocker_id}`;
    const steps = document.createElement("ol");
    for (const step of play.support_steps || []) {
      const li = document.createElement("li");
      li.textContent = step;
      steps.appendChild(li);
    }
    const reply = document.createElement("p");
    reply.textContent = `Player reply: ${play.player_reply_template || ""}`;
    const product = document.createElement("p");
    product.textContent = `Product fix: ${play.product_fix_suggestion || ""}`;
    item.append(title, steps, reply, product);
    playbookList.appendChild(item);
  }
}

function renderBacklog(backlog) {
  backlogSummary.textContent = backlog.summary || "No backlog summary available.";
  backlogList.innerHTML = "";
  const items = Array.isArray(backlog.backlog_items) ? backlog.backlog_items : [];
  if (!items.length) {
    backlogList.textContent = "No product backlog items are available for the current filters.";
    return;
  }
  for (const backlogItem of items) {
    const item = document.createElement("article");
    item.className = "support-backlog-item";
    const title = document.createElement("strong");
    title.textContent = `${backlogItem.priority} · ${backlogItem.title} · ${backlogItem.affected_cases} cases`;
    const fix = document.createElement("p");
    fix.textContent = `Fix: ${backlogItem.product_fix_suggestion}`;
    const signal = document.createElement("p");
    signal.textContent = `Signal: ${backlogItem.support_signal}`;
    const criteria = document.createElement("ul");
    for (const criterion of backlogItem.acceptance_criteria || []) {
      const li = document.createElement("li");
      li.textContent = criterion;
      criteria.appendChild(li);
    }
    item.append(title, fix, signal, criteria);
    backlogList.appendChild(item);
  }
}

function exportBacklog(format) {
  window.location.href = `/account/debug-bundle/review/audit/backlog?${auditQueryString(format)}`;
}

function renderAuditRecords(records) {
  auditList.innerHTML = "";
  if (!records.length) {
    auditList.textContent = "No audit records saved yet.";
    return;
  }
  for (const record of records) {
    const item = document.createElement("article");
    item.className = `support-audit-record ${record.highest_severity || "info"}`;
    const title = document.createElement("strong");
    title.textContent = `${record.overall_status} · ${record.case_id}`;
    const meta = document.createElement("span");
    meta.textContent = `${record.created_at} · reviewer: ${record.reviewer || "support"} · findings: ${(record.finding_ids || []).join(", ") || "none"}`;
    const reply = document.createElement("p");
    reply.textContent = record.reply_template_summary || "No reply summary stored.";
    item.append(title, meta, reply);
    auditList.appendChild(item);
  }
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
  lastBundle = null;
  lastReview = null;
  summary.textContent = "No bundle reviewed yet.";
  findingList.innerHTML = "";
  replyTemplate.value = "";
  output.textContent = "{}";
});

saveAuditButton?.addEventListener("click", saveAuditRecord);

refreshAuditButton?.addEventListener("click", refreshAuditRecords);

exportAuditButton?.addEventListener("click", exportAuditCsv);

refreshMetricsButton?.addEventListener("click", refreshAuditMetrics);

refreshPlaybookButton?.addEventListener("click", refreshPlaybook);

refreshBacklogButton?.addEventListener("click", refreshBacklog);

exportBacklogMdButton?.addEventListener("click", () => exportBacklog("markdown"));

exportBacklogCsvButton?.addEventListener("click", () => exportBacklog("csv"));

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
