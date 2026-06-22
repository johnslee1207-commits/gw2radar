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
const refreshPromotionsButton = document.querySelector("#refresh-promotions-button");
const exportPromotionsMdButton = document.querySelector("#export-promotions-md-button");
const exportPromotionsCsvButton = document.querySelector("#export-promotions-csv-button");
const refreshPromotionEventsButton = document.querySelector("#refresh-promotion-events-button");
const exportPromotionEventsMdButton = document.querySelector("#export-promotion-events-md-button");
const exportPromotionEventsCsvButton = document.querySelector("#export-promotion-events-csv-button");
const refreshPromotionReadinessButton = document.querySelector("#refresh-promotion-readiness-button");
const exportPromotionReadinessMdButton = document.querySelector("#export-promotion-readiness-md-button");
const exportPromotionReadinessCsvButton = document.querySelector("#export-promotion-readiness-csv-button");
const saveGatewayNoteButton = document.querySelector("#save-gateway-note-button");
const refreshGatewayNotesButton = document.querySelector("#refresh-gateway-notes-button");
const exportGatewayNotesMdButton = document.querySelector("#export-gateway-notes-md-button");
const exportGatewayNotesCsvButton = document.querySelector("#export-gateway-notes-csv-button");
const refreshIncidentDashboardButton = document.querySelector("#refresh-incident-dashboard-button");
const writeIncidentPacketButton = document.querySelector("#write-incident-packet-button");
const loadIncidentPacketsButton = document.querySelector("#load-incident-packets-button");
const loadIncidentPacketZipButton = document.querySelector("#load-incident-packet-zip-button");
const verifyIncidentPacketZipButton = document.querySelector("#verify-incident-packet-zip-button");
const exportIncidentDashboardMdButton = document.querySelector("#export-incident-dashboard-md-button");
const exportIncidentDashboardCsvButton = document.querySelector("#export-incident-dashboard-csv-button");
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
const promotionSummary = document.querySelector("#promotion-summary");
const promotionList = document.querySelector("#promotion-list");
const promotionEventSummary = document.querySelector("#promotion-event-summary");
const promotionEventList = document.querySelector("#promotion-event-list");
const promotionReadinessSummary = document.querySelector("#promotion-readiness-summary");
const promotionReadinessStatusList = document.querySelector("#promotion-readiness-status-list");
const promotionReadinessBlockerList = document.querySelector("#promotion-readiness-blocker-list");
const promotionReadinessNextStepList = document.querySelector("#promotion-readiness-next-step-list");
const gatewayNoteSnapshotId = document.querySelector("#gateway-note-snapshot-id");
const gatewayNoteStatus = document.querySelector("#gateway-note-status");
const gatewayNoteAssignee = document.querySelector("#gateway-note-assignee");
const gatewayNoteBody = document.querySelector("#gateway-note-body");
const gatewayNoteSummary = document.querySelector("#gateway-note-summary");
const gatewayNoteList = document.querySelector("#gateway-note-list");
const incidentDashboardSummary = document.querySelector("#incident-dashboard-summary");
const incidentDashboardCards = document.querySelector("#incident-dashboard-cards");
const incidentPacketZipSummary = document.querySelector("#incident-packet-zip-summary");
const incidentPacketList = document.querySelector("#incident-packet-list");
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
  await refreshPromotionReadiness();
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

async function refreshPromotions() {
  const response = await fetch(`/account/debug-bundle/review/audit/backlog/promotions?${promotionQueryString()}`);
  const bundle = await response.json();
  renderPromotions(bundle);
}

async function refreshPromotionEvents() {
  const response = await fetch(`/account/debug-bundle/review/audit/backlog/promotions/events?${promotionEventQueryString()}`);
  const bundle = await response.json();
  renderPromotionEvents(bundle);
}

async function refreshPromotionReadiness() {
  const response = await fetch(`/account/debug-bundle/review/audit/backlog/promotions/readiness?${promotionReadinessQueryString()}`);
  const rollup = await response.json();
  renderPromotionReadiness(rollup);
}

async function saveGatewayIncidentNote() {
  const response = await fetch("/api/v1/player/gateway-incidents/review-notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      snapshot_id: gatewayNoteSnapshotId?.value?.trim() || null,
      status: gatewayNoteStatus?.value || "open",
      reviewer: reviewerName?.value || "support",
      assignee: gatewayNoteAssignee?.value || "unassigned",
      note: gatewayNoteBody?.value || "",
      source: "support_workbench",
    }),
  });
  const payload = await response.json();
  output.textContent = JSON.stringify(payload, null, 2);
  gatewayNoteSummary.textContent = `Gateway note saved: ${payload.data?.review_note?.note_id || "unknown"}.`;
  await refreshGatewayIncidentNotes();
}

async function refreshGatewayIncidentNotes() {
  const response = await fetch(`/api/v1/player/gateway-incidents/review-notes?${gatewayNoteQueryString()}`);
  const payload = await response.json();
  const bundle = payload.data?.review_notes || payload.review_notes || {};
  renderGatewayIncidentNotes(bundle);
}

function gatewayNoteQueryString(format = "json") {
  const params = new URLSearchParams();
  params.set("limit", "20");
  params.set("format", format);
  if (gatewayNoteStatus?.value) {
    params.set("status", gatewayNoteStatus.value);
  }
  if (reviewerName?.value) {
    params.set("reviewer", reviewerName.value.trim());
  }
  if (gatewayNoteAssignee?.value) {
    params.set("assignee", gatewayNoteAssignee.value.trim());
  }
  if (gatewayNoteSnapshotId?.value) {
    params.set("snapshot_id", gatewayNoteSnapshotId.value.trim());
  }
  return params.toString();
}

function exportGatewayIncidentNotes(format) {
  window.location.href = `/api/v1/player/gateway-incidents/review-notes?${gatewayNoteQueryString(format)}`;
}

async function refreshSupportCaseIncidentDashboard() {
  const response = await fetch("/api/v1/player/support-case/incident-dashboard?limit=20");
  const payload = await response.json();
  const dashboard = payload.data?.support_case_incident_dashboard || {};
  renderSupportCaseIncidentDashboard(dashboard);
  output.textContent = JSON.stringify(payload, null, 2);
}

function exportSupportCaseIncidentDashboard(format) {
  window.location.href = `/api/v1/player/support-case/incident-dashboard?format=${format}&limit=20`;
}

async function writeSupportCaseIncidentPacket() {
  const response = await fetch("/api/v1/player/support-case/incident-packet?limit=20", { method: "POST" });
  const payload = await response.json();
  output.textContent = JSON.stringify(payload, null, 2);
  incidentDashboardSummary.textContent = `Support case incident packet written: ${payload.data?.support_case_incident_packet?.packet_id || "unknown"}.`;
  await loadSupportCaseIncidentPackets();
}

async function loadSupportCaseIncidentPackets() {
  const response = await fetch("/api/v1/player/support-case/incident-packet?limit=10");
  const payload = await response.json();
  renderSupportCaseIncidentPackets(payload.data?.support_case_incident_packets || []);
}

async function loadSupportCaseIncidentPacketZipManifest() {
  const response = await fetch("/api/v1/player/support-case/incident-packet/bundle?format=manifest");
  const payload = await response.json();
  const manifest = payload.data?.support_case_incident_packet_zip_bundle || {};
  incidentPacketZipSummary.textContent = `${manifest.file_count || 0} zip files · checksum ${manifest.checksum_sha256 || "none"}.`;
  output.textContent = JSON.stringify(payload, null, 2);
}

async function verifySupportCaseIncidentPacketZip() {
  const response = await fetch("/api/v1/player/support-case/incident-packet/bundle/verify", { method: "POST" });
  const payload = await response.json();
  const verification = payload.data?.support_case_incident_packet_zip_verification || {};
  incidentPacketZipSummary.textContent = `Zip verification ${verification.ready ? "ready" : "blocked"} · ${verification.file_count || 0} files · checksum ${verification.checksum_sha256 || "none"}.`;
  output.textContent = JSON.stringify(payload, null, 2);
}

function renderSupportCaseIncidentDashboard(dashboard) {
  const cards = Array.isArray(dashboard.status_cards) ? dashboard.status_cards : [];
  incidentDashboardSummary.textContent = `${dashboard.support_status || "unknown"} · ${dashboard.maturity_label || "unknown"} · gateway notes ${dashboard.gateway_note_count || 0} · support audits ${dashboard.support_audit_count || 0}.`;
  incidentDashboardCards.innerHTML = "";
  if (!cards.length) {
    incidentDashboardCards.textContent = "No incident dashboard cards are available yet.";
    return;
  }
  for (const card of cards) {
    const item = document.createElement("article");
    item.className = "support-backlog-item";
    const title = document.createElement("strong");
    title.textContent = `${card.label || card.card_id} · ${card.status || "unknown"}`;
    const summaryText = document.createElement("p");
    summaryText.textContent = card.summary || "";
    item.append(title, summaryText);
    incidentDashboardCards.appendChild(item);
  }
}

function renderSupportCaseIncidentPackets(packets) {
  incidentPacketList.innerHTML = "";
  if (!packets.length) {
    incidentPacketList.textContent = "No support case incident packets are available yet.";
    return;
  }
  for (const packet of packets) {
    const item = document.createElement("article");
    item.className = "support-audit-record info";
    const title = document.createElement("strong");
    title.textContent = `${packet.support_status || "unknown"} · ${packet.packet_id}`;
    const meta = document.createElement("span");
    meta.textContent = `${packet.file_count || 0} files · checksum ${packet.checksum_sha256 || "none"}`;
    const links = document.createElement("p");
    links.textContent = `Manifest: /api/v1/player/support-case/incident-packet/${packet.packet_id}/manifest.json`;
    item.append(title, meta, links);
    incidentPacketList.appendChild(item);
  }
}

function renderGatewayIncidentNotes(bundle) {
  const notes = Array.isArray(bundle.notes) ? bundle.notes : [];
  gatewayNoteSummary.textContent = `${notes.length} notes · open ${bundle.open_count || 0} · assigned ${bundle.assigned_count || 0} · closed ${bundle.closed_count || 0}.`;
  gatewayNoteList.innerHTML = "";
  if (!notes.length) {
    gatewayNoteList.textContent = "No gateway incident notes match the current filters.";
    return;
  }
  for (const note of notes) {
    const item = document.createElement("article");
    item.className = `support-audit-record ${note.status || "open"}`;
    const title = document.createElement("strong");
    title.textContent = `${note.status} · ${note.note_id}`;
    const meta = document.createElement("span");
    meta.textContent = `${note.snapshot_id || "no snapshot"} · reviewer: ${note.reviewer || "support"} · assignee: ${note.assignee || "unassigned"}`;
    const body = document.createElement("p");
    body.textContent = note.note || "No note provided.";
    const actions = document.createElement("div");
    actions.className = "button-row";
    for (const [status, label] of [
      ["closed", "Close"],
      ["deferred", "Defer"],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => updateGatewayIncidentNoteStatus(note.note_id, status));
      actions.appendChild(button);
    }
    item.append(title, meta, actions, body);
    gatewayNoteList.appendChild(item);
  }
}

async function updateGatewayIncidentNoteStatus(noteId, status) {
  const response = await fetch(`/api/v1/player/gateway-incidents/review-notes/${noteId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status,
      reviewer: reviewerName?.value || "support",
      assignee: gatewayNoteAssignee?.value || "support",
      note: `Support marked gateway incident note ${status}.`,
    }),
  });
  const payload = await response.json();
  output.textContent = JSON.stringify(payload, null, 2);
  gatewayNoteSummary.textContent = `Gateway note ${noteId} marked ${status}.`;
  await refreshGatewayIncidentNotes();
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
    const promote = document.createElement("button");
    promote.type = "button";
    promote.textContent = "Promote draft";
    promote.addEventListener("click", () => promoteBacklogItem(backlogItem.backlog_id));
    const criteria = document.createElement("ul");
    for (const criterion of backlogItem.acceptance_criteria || []) {
      const li = document.createElement("li");
      li.textContent = criterion;
      criteria.appendChild(li);
    }
    item.append(title, fix, signal, promote, criteria);
    backlogList.appendChild(item);
  }
}

function exportBacklog(format) {
  window.location.href = `/account/debug-bundle/review/audit/backlog?${auditQueryString(format)}`;
}

async function promoteBacklogItem(backlogId) {
  const body = {
    backlog_id: backlogId,
    reviewer: reviewerName?.value || "support",
    audit_reviewer: auditReviewerFilter?.value?.trim() || null,
    status: auditStatusFilter?.value?.trim() || null,
    severity: auditSeverityFilter?.value || null,
    artifact_type: "roadmap_issue_draft",
    source: "support_workbench",
  };
  const response = await fetch("/account/debug-bundle/review/audit/backlog/promotions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  output.textContent = JSON.stringify(payload, null, 2);
  if (payload.status === "created") {
    summary.textContent = `Promotion draft created: ${payload.promotion?.promotion_id || "unknown"}.`;
    await refreshPromotions();
    await refreshPromotionReadiness();
  } else {
    summary.textContent = `Promotion draft not created: ${payload.status || "unknown"}.`;
  }
}

function promotionQueryString(format = "json") {
  const params = new URLSearchParams();
  params.set("limit", "10");
  params.set("format", format);
  if (reviewerName?.value) {
    params.set("reviewer", reviewerName.value.trim());
  }
  return params.toString();
}

function exportPromotions(format) {
  window.location.href = `/account/debug-bundle/review/audit/backlog/promotions?${promotionQueryString(format)}`;
}

function renderPromotions(bundle) {
  const promotions = Array.isArray(bundle.promotions) ? bundle.promotions : [];
  promotionSummary.textContent = `${promotions.length} promotion drafts loaded.`;
  promotionList.innerHTML = "";
  if (!promotions.length) {
    promotionList.textContent = "No promotion drafts match the current reviewer filter.";
    return;
  }
  for (const promotion of promotions) {
    const item = document.createElement("article");
    item.className = "support-promotion-item";
    const title = document.createElement("strong");
    title.textContent = `${promotion.priority} · ${promotion.title} · ${promotion.status}`;
    const meta = document.createElement("span");
    meta.textContent = `${promotion.promotion_id} · backlog: ${promotion.backlog_id} · reviewer: ${promotion.reviewer}`;
    const body = document.createElement("pre");
    body.textContent = promotion.body_markdown || "";
    const actions = document.createElement("div");
    actions.className = "button-row";
    for (const [status, label] of [
      ["accepted", "Accept"],
      ["linked", "Mark linked"],
      ["closed", "Close"],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => updatePromotionStatus(promotion.promotion_id, status));
      actions.appendChild(button);
    }
    item.append(title, meta, actions, body);
    promotionList.appendChild(item);
  }
}

async function updatePromotionStatus(promotionId, status) {
  const response = await fetch(`/account/debug-bundle/review/audit/backlog/promotions/${promotionId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status,
      reviewer: reviewerName?.value || "support",
      note: `Operator marked promotion ${status}.`,
    }),
  });
  const payload = await response.json();
  output.textContent = JSON.stringify(payload, null, 2);
  if (payload.status === "updated") {
    summary.textContent = `Promotion ${promotionId} marked ${status}.`;
    await refreshPromotions();
    await refreshPromotionEvents();
    await refreshPromotionReadiness();
  } else {
    summary.textContent = `Promotion status not updated: ${payload.status || "unknown"}.`;
  }
}

function promotionEventQueryString(format = "json") {
  const params = new URLSearchParams();
  params.set("limit", "20");
  params.set("format", format);
  return params.toString();
}

function exportPromotionEvents(format) {
  window.location.href = `/account/debug-bundle/review/audit/backlog/promotions/events?${promotionEventQueryString(format)}`;
}

function promotionReadinessQueryString(format = "json") {
  const params = new URLSearchParams();
  params.set("audit_limit", "100");
  params.set("promotion_limit", "100");
  params.set("event_limit", "100");
  params.set("format", format);
  if (auditStatusFilter?.value) {
    params.set("status", auditStatusFilter.value.trim());
  }
  if (auditSeverityFilter?.value) {
    params.set("severity", auditSeverityFilter.value);
  }
  if (auditReviewerFilter?.value) {
    params.set("audit_reviewer", auditReviewerFilter.value.trim());
  }
  if (reviewerName?.value) {
    params.set("promotion_reviewer", reviewerName.value.trim());
  }
  return params.toString();
}

function exportPromotionReadiness(format) {
  window.location.href = `/account/debug-bundle/review/audit/backlog/promotions/readiness?${promotionReadinessQueryString(format)}`;
}

function renderPromotionEvents(bundle) {
  const events = Array.isArray(bundle.events) ? bundle.events : [];
  promotionEventSummary.textContent = `${events.length} promotion events loaded.`;
  promotionEventList.innerHTML = "";
  if (!events.length) {
    promotionEventList.textContent = "No promotion events are available yet.";
    return;
  }
  for (const event of events) {
    const item = document.createElement("article");
    item.className = "support-promotion-item";
    const title = document.createElement("strong");
    title.textContent = `${event.action} · ${event.previous_status || "none"} → ${event.new_status || "none"}`;
    const meta = document.createElement("span");
    meta.textContent = `${event.event_id} · ${event.promotion_id} · reviewer: ${event.reviewer}`;
    const note = document.createElement("p");
    note.textContent = event.note || "No note.";
    item.append(title, meta, note);
    promotionEventList.appendChild(item);
  }
}

function renderPromotionReadiness(rollup) {
  const score = typeof rollup.readiness_score === "number" ? rollup.readiness_score.toFixed(1) : "0.0";
  promotionReadinessSummary.textContent = `${rollup.maturity_label || "unknown"} · ${score}/100 · ${rollup.summary || "No readiness summary available."}`;
  renderMetricList(promotionReadinessStatusList, [
    { key: "ready", count: rollup.ready ? 1 : 0 },
    { key: "audit_records", count: rollup.audit_total || 0 },
    { key: "backlog_items", count: rollup.backlog_total || 0 },
    { key: "promotion_drafts", count: rollup.promotion_total || 0 },
    { key: "promotion_events", count: rollup.event_total || 0 },
  ]);
  renderTextList(promotionReadinessBlockerList, rollup.blockers || []);
  renderTextList(promotionReadinessNextStepList, rollup.next_steps || []);
}

function renderTextList(target, rows) {
  target.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("li");
    empty.textContent = "None";
    target.appendChild(empty);
    return;
  }
  for (const row of rows) {
    const item = document.createElement("li");
    item.textContent = row;
    target.appendChild(item);
  }
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

refreshPromotionsButton?.addEventListener("click", refreshPromotions);

exportPromotionsMdButton?.addEventListener("click", () => exportPromotions("markdown"));

exportPromotionsCsvButton?.addEventListener("click", () => exportPromotions("csv"));

refreshPromotionEventsButton?.addEventListener("click", refreshPromotionEvents);

exportPromotionEventsMdButton?.addEventListener("click", () => exportPromotionEvents("markdown"));

exportPromotionEventsCsvButton?.addEventListener("click", () => exportPromotionEvents("csv"));

refreshPromotionReadinessButton?.addEventListener("click", refreshPromotionReadiness);

exportPromotionReadinessMdButton?.addEventListener("click", () => exportPromotionReadiness("markdown"));

exportPromotionReadinessCsvButton?.addEventListener("click", () => exportPromotionReadiness("csv"));

saveGatewayNoteButton?.addEventListener("click", saveGatewayIncidentNote);

refreshGatewayNotesButton?.addEventListener("click", refreshGatewayIncidentNotes);

exportGatewayNotesMdButton?.addEventListener("click", () => exportGatewayIncidentNotes("markdown"));

exportGatewayNotesCsvButton?.addEventListener("click", () => exportGatewayIncidentNotes("csv"));

refreshIncidentDashboardButton?.addEventListener("click", refreshSupportCaseIncidentDashboard);

writeIncidentPacketButton?.addEventListener("click", writeSupportCaseIncidentPacket);

loadIncidentPacketsButton?.addEventListener("click", loadSupportCaseIncidentPackets);

loadIncidentPacketZipButton?.addEventListener("click", loadSupportCaseIncidentPacketZipManifest);

verifyIncidentPacketZipButton?.addEventListener("click", verifySupportCaseIncidentPacketZip);

exportIncidentDashboardMdButton?.addEventListener("click", () => exportSupportCaseIncidentDashboard("markdown"));

exportIncidentDashboardCsvButton?.addEventListener("click", () => exportSupportCaseIncidentDashboard("csv"));

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
