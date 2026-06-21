const state = {
  activeBuildId: "",
  lastCheckoutId: "",
  playerIntent: "",
  characterSnapshots: [],
  selectedAccountGear: null,
  buildUpgradeRules: [],
  lastRouteFetchRequest: null,
  lastRoutePromotionSourceId: "",
  lastRouteRemediationItemId: "",
  lastRouteBackfillCandidateId: "",
  lastRouteSourcePatchDraftId: "",
  lastRouteDraftSourceId: "",
};

const storageKeys = {
  activeView: "gw2radar.player.activeView",
  activeBuildId: "gw2radar.player.activeBuildId",
  playerIntent: "gw2radar.player.intent",
  reportHistory: "gw2radar.player.reportHistory",
};

const outputs = {
  welcome: document.querySelector("#dashboard-output"),
  dashboard: document.querySelector("#dashboard-output"),
  connect: document.querySelector("#connect-output"),
  returner: document.querySelector("#returner-output"),
  legendary: document.querySelector("#legendary-output"),
  routes: document.querySelector("#routes-output"),
  build: document.querySelector("#build-output"),
  reports: document.querySelector("#reports-output"),
  freshness: document.querySelector("#freshness-output"),
  privacy: document.querySelector("#privacy-output"),
};

const summaries = {
  welcome: document.querySelector("#welcome-summary"),
  dashboard: document.querySelector("#dashboard-summary"),
  connect: document.querySelector("#connect-summary"),
  returner: document.querySelector("#returner-summary"),
  legendary: document.querySelector("#legendary-summary"),
  routes: document.querySelector("#routes-summary"),
  build: document.querySelector("#build-summary"),
  reports: document.querySelector("#reports-summary"),
  freshness: document.querySelector("#freshness-summary"),
  privacy: document.querySelector("#privacy-summary"),
};

function readStorage(key, fallback = "") {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Local UI state is optional; backend data is unaffected.
  }
}

function removeStorage(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // Ignore unavailable browser storage.
  }
}

function showView(viewId) {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active-view", view.id === viewId);
  });
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewId);
  });
  writeStorage(storageKeys.activeView, viewId);
}

function render(target, value) {
  const element = outputs[target] || outputs.dashboard;
  element.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function renderSummary(target, value) {
  const element = summaries[target];
  if (element) {
    element.textContent = value;
  }
}

function markStep(step, label, ready = true) {
  const stepText = document.querySelector(`#step-${step}`);
  const stepCard = document.querySelector(`[data-step="${step}"]`);
  if (stepText) {
    stepText.textContent = label;
  }
  if (stepCard) {
    stepCard.classList.toggle("ready", ready);
  }
}

function renderActionList(selector, actions) {
  const list = document.querySelector(selector);
  if (!list || !Array.isArray(actions)) {
    return;
  }
  list.innerHTML = "";
  for (const action of actions) {
    const item = document.createElement("li");
    item.textContent = action.reason ? `${action.title} - ${action.reason}` : action.title;
    list.appendChild(item);
  }
}

function summarizeResult(target, payload) {
  const data = payload?.data || payload;
  if (target === "dashboard") {
    if (data?.readiness?.data?.readiness) {
      const readiness = data.readiness.data.readiness;
      return `Player readiness ${readiness.readiness_label}: ${readiness.readiness_score}/100 across ${readiness.checks?.length || 0} checks.`;
    }
    if (data?.correlation?.data?.correlation) {
      const correlation = data.correlation.data.correlation;
      return `History correlation ${correlation.status}: readiness delta ${correlation.readiness_score_delta || 0}, price coverage delta ${correlation.price_coverage_delta || 0}.`;
    }
    if (data?.correlation?.schema_version === "gw2radar.player_history_correlation.v1") {
      return `History correlation ${data.correlation.status}: readiness delta ${data.correlation.readiness_score_delta || 0}, price coverage delta ${data.correlation.price_coverage_delta || 0}.`;
    }
    if (data?.session_packet?.schema_version === "gw2radar.player_session_packet.v1") {
      return `Session packet ready: ${data.session_packet.debug_safe_evidence?.length || 0} evidence rows and ${data.session_packet.support_review_prompts?.length || 0} support prompts.`;
    }
    if (data?.sessionPacket?.data?.session_packet) {
      const packet = data.sessionPacket.data.session_packet;
      return `Session packet ready: ${packet.debug_safe_evidence?.length || 0} evidence rows and ${packet.support_review_prompts?.length || 0} support prompts.`;
    }
    if (data?.refresh?.data?.official_price_refresh) {
      const refresh = data.refresh.data.official_price_refresh;
      return `Official price refresh ${refresh.status}: ${refresh.refreshed_item_count || 0}/${refresh.requested_item_count || 0} items refreshed.`;
    }
    if (data?.dashboard) {
      const count = data.dashboard.today_best_actions?.length || 0;
      return `${count} account-aware best actions loaded with freshness annotations.`;
    }
    return "Dashboard refreshed. Check connection and sync status before acting on account-aware plans.";
  }
  if (target === "welcome") {
    return "Player intent selected. Connect and sync before trusting account-aware recommendations.";
  }
  if (target === "connect") {
    if (data?.schema_version === "gw2radar.account_debug_bundle.v1") {
      const status = data.diagnostic_summary?.summary_status || "unknown";
      const actionCount = data.diagnostic_summary?.next_actions?.length || 0;
      return `Debug bundle exported: diagnostic status ${status}, ${actionCount} next actions included.`;
    }
    if (data?.schema_version === "gw2radar.account_connection_diagnostic.v1") {
      const failed = data.checks?.filter((check) => check.status === "fail").length || 0;
      const warnings = data.checks?.filter((check) => check.status === "warn").length || 0;
      if (data.summary_status === "ready") {
        return "Connection diagnostic ready: key, permissions, sync snapshot, and Build Fit bridge are available.";
      }
      return `Connection diagnostic needs attention: ${failed} failed checks and ${warnings} warnings.`;
    }
    if (data?.schema_version === "gw2radar.api_key_permissions.v1") {
      const missingRequired = data.missing_required_permissions?.length || 0;
      const mode = data.limited_mode ? "limited mode" : "ready";
      return `${mode}: ${missingRequired} required permissions missing. Sync only after reviewing affected features.`;
    }
    if (data?.drained) {
      const status = data.drained.status || "unknown";
      if (status === "succeeded") {
        const updated = data.drained.updated_player_state || 0;
        const snapshots = data.character_snapshots?.data?.snapshots?.length || 0;
        return `Sync succeeded: ${updated} private account records updated and ${snapshots} character snapshots loaded.`;
      }
      if (status === "delayed") {
        return "Sync was delayed. Check endpoint progress and retry after the GW2 API backoff window.";
      }
      if (status === "idle") {
        return "No queued sync job was available. Queue sync again if you expected a refresh.";
      }
      return `Sync workflow completed with status: ${status}. Review the JSON output.`;
    }
    if (data?.status === "queued") {
      return "Sync queued. In local development, run Sync now or Drain one job to write account data.";
    }
    if (data?.status === "succeeded") {
      return `Sync succeeded: ${data.updated_player_state || 0} private account records updated.`;
    }
    if (data?.counts) {
      return `Sync status checked. Queued: ${data.counts.queued || 0}, succeeded: ${data.counts.succeeded || 0}, delayed: ${data.counts.retry_scheduled || 0}.`;
    }
    if (typeof data?.is_configured === "boolean") {
      return data.is_configured ? "API key is stored. Check permissions, then run Sync now." : "No API key stored.";
    }
    return "Connection workflow updated. Run sync before trusting private account state.";
  }
  if (target === "returner") {
    if (data?.readiness) {
      return `Returner readiness is ${data.readiness.overall_score}/100 (${data.readiness.overall_status}). Review low dimensions before costly goals.`;
    }
    if (Array.isArray(payload)) {
      return `${payload.length} goals loaded. Pick one goal before generating a short action plan.`;
    }
    const missing = data?.missing_requirements?.length;
    if (typeof missing === "number") {
      return `${missing} missing requirements found. Treat unknown facts as assumptions.`;
    }
    return "Returner output updated. Review assumptions before following the plan.";
  }
  if (target === "legendary") {
    if (data?.action_plan) {
      return "Legendary today and this-week route loaded with cheap, fast, and balanced path context.";
    }
    if (data?.goals) {
      return `${data.goals.length} legendary goal choices loaded. Add the goals you want to compare.`;
    }
    const doNotSell = data?.do_not_sell?.length;
    if (typeof doNotSell === "number") {
      return `${doNotSell} do-not-sell entries need manual review before selling materials.`;
    }
    if (data?.goal_cost_index) {
      return "Goal cost index updated from manual price snapshots and current goal gap.";
    }
    return "Legendary planning output updated. Market signals are observation-only.";
  }
  if (target === "routes") {
    if (data?.fetch_preview) {
      const fetched = data.fetch_preview.fetched_achievement_ids?.length || 0;
      const missing = data.fetch_preview.missing_achievement_ids?.length || 0;
      return `${fetched} official achievements fetched, ${missing} missing. Preview remains draft until reviewed promotion.`;
    }
    if (data?.promotion) {
      return `${data.promotion.manifest?.steps?.length || 0} reviewed route steps promoted for planner ingestion.`;
    }
    if (data?.audit) {
      return `${data.audit.records?.length || 0} route promotion audit records loaded.`;
    }
    if (data?.readiness) {
      return `Route release readiness is ${data.readiness.maturity_label} at ${data.readiness.readiness_score}/100.`;
    }
    if (data?.quality) {
      return `Route source quality is ${data.quality.maturity_label} at ${data.quality.overall_score}/100 across ${data.quality.step_reviews?.length || 0} steps.`;
    }
    if (data?.remediation_queue) {
      return `${data.remediation_queue.open_item_count || 0} route remediation items open, including ${data.remediation_queue.p0_count || 0} P0 blockers.`;
    }
    if (data?.remediation_review) {
      return `Remediation item ${data.remediation_review.item_id} marked ${data.remediation_review.status} by ${data.remediation_review.reviewer}.`;
    }
    if (data?.remediation_review_audit) {
      return `${data.remediation_review_audit.records?.length || 0} remediation review audit records loaded.`;
    }
    if (data?.remediation_readiness) {
      return `Remediation readiness is ${data.remediation_readiness.maturity_label} at ${data.remediation_readiness.readiness_score}/100.`;
    }
    if (data?.operator_action_bundle) {
      return `Operator bundle loaded: quality ${data.operator_action_bundle.quality?.maturity_label}, remediation ${data.operator_action_bundle.remediation_readiness?.maturity_label}.`;
    }
    if (data?.operator_release_packet) {
      return `Release packet is ${data.operator_release_packet.maturity_label} with ${data.operator_release_packet.blocker_count} blockers.`;
    }
    if (data?.backfill_candidates) {
      return `${data.backfill_candidates.candidate_count || 0} draft backfill candidates generated for manual source edits.`;
    }
    if (data?.backfill_candidate_review) {
      return `Backfill candidate ${data.backfill_candidate_review.candidate_id} marked ${data.backfill_candidate_review.status} by ${data.backfill_candidate_review.reviewer}.`;
    }
    if (data?.backfill_candidate_review_audit) {
      return `${data.backfill_candidate_review_audit.records?.length || 0} backfill candidate audit records loaded.`;
    }
    if (data?.backfill_candidate_readiness) {
      return `Backfill candidate readiness is ${data.backfill_candidate_readiness.maturity_label} at ${data.backfill_candidate_readiness.readiness_score}/100.`;
    }
    if (data?.source_edit_patch_draft) {
      return `${data.source_edit_patch_draft.draft_count || 0} source edit patch drafts with ${data.source_edit_patch_draft.operation_count || 0} operations generated for manual review.`;
    }
    if (data?.source_edit_patch_apply) {
      state.lastRouteDraftSourceId = data.source_edit_patch_apply.output_source_id || state.lastRouteDraftSourceId;
      return `Source patch draft ${data.source_edit_patch_apply.draft_id} applied to draft manifest ${data.source_edit_patch_apply.output_source_id}.`;
    }
    if (data?.source_edit_patch_apply_audit) {
      return `${data.source_edit_patch_apply_audit.records?.length || 0} source patch apply audit records loaded.`;
    }
    if (data?.draft_source_promotion) {
      state.lastRoutePromotionSourceId = data.draft_source_promotion.reviewed_source_id || state.lastRoutePromotionSourceId;
      return `Draft source ${data.draft_source_promotion.draft_source_id} promoted to reviewed source ${data.draft_source_promotion.reviewed_source_id}.`;
    }
    if (data?.draft_source_promotion_audit) {
      return `${data.draft_source_promotion_audit.records?.length || 0} draft source promotion audit records loaded.`;
    }
    if (data?.release_evidence_bundle) {
      return `Release evidence bundle ${data.release_evidence_bundle.maturity_label}: ${data.release_evidence_bundle.reviewed_source_count} sources, ${data.release_evidence_bundle.blocker_count} blockers.`;
    }
    if (data?.release_evidence_archive) {
      return `Release evidence archived by ${data.release_evidence_archive.archived_by}: ${data.release_evidence_archive.archive_id}.`;
    }
    if (data?.release_evidence_archive_index) {
      return `Release evidence archive: ${data.release_evidence_archive_index.total_records} records.`;
    }
    if (data?.release_evidence_archive_diff) {
      return `Release evidence diff ${data.release_evidence_archive_diff.maturity_label}: ${data.release_evidence_archive_diff.regression_count} regressions, ${data.release_evidence_archive_diff.improvement_count} improvements.`;
    }
    if (data?.release_signoff) {
      return `Release sign-off ${data.release_signoff.status}: ${data.release_signoff.reviewer}, ${data.release_signoff.regression_count} regressions.`;
    }
    if (data?.release_signoff_audit) {
      return `${data.release_signoff_audit.records?.length || 0} release sign-off audit records loaded.`;
    }
    if (data?.operator_release_dashboard) {
      return `Release dashboard ${data.operator_release_dashboard.maturity_label}: ${data.operator_release_dashboard.blockers?.length || 0} blockers, ${data.operator_release_dashboard.missing_gates?.length || 0} missing gates.`;
    }
    if (data?.release_export_packet) {
      return `Release export packet ${data.release_export_packet.maturity_label}: ${data.release_export_packet.artifact_count} artifacts.`;
    }
    if (data?.release_export_artifacts) {
      return `Release export artifacts: ${data.release_export_artifacts.file_count} files indexed.`;
    }
    if (data?.release_export_bundle) {
      return `Release export bundle: ${data.release_export_bundle.file_count} files, ${data.release_export_bundle.size_bytes} bytes.`;
    }
    if (data?.release_export_bundle_verification) {
      return `Release export bundle verification: ${data.release_export_bundle_verification.ready ? "ready" : "blocked"} with ${data.release_export_bundle_verification.blockers.length} blockers.`;
    }
    if (data?.release_export_bundle_verification_audit_record) {
      return `Release bundle verification audit: ${data.release_export_bundle_verification_audit_record.ready ? "ready" : "blocked"} by ${data.release_export_bundle_verification_audit_record.reviewer}.`;
    }
    if (data?.release_export_bundle_verification_audit) {
      return `Release bundle verification audit records: ${data.release_export_bundle_verification_audit.records.length}.`;
    }
    if (data?.operator_handoff_checklist) {
      return `Operator handoff checklist: ${data.operator_handoff_checklist.maturity_label} with ${data.operator_handoff_checklist.missing_gates.length} missing gates.`;
    }
    if (data?.release_notes) {
      return `Release notes: ${data.release_notes.maturity_label}, ${data.release_notes.highlights.length} highlights.`;
    }
    if (data?.operator_runbook) {
      return `Operator runbook: ${data.operator_runbook.maturity_label}, ${data.operator_runbook.preflight_steps.length} preflight steps.`;
    }
    if (data?.final_release_dashboard) {
      return `Final release dashboard: ${data.final_release_dashboard.maturity_label}.`;
    }
    if (data?.final_maturity_audit) {
      return `Final maturity audit: ${data.final_maturity_audit.complete_player_ui_items} complete UI items.`;
    }
    if (Array.isArray(data?.sources)) {
      return `${data.sources.length} route source manifests loaded with ${data.reviewed_step_count || 0} reviewed steps.`;
    }
    if (data?.plan) {
      const plan = data.plan;
      return `${plan.ready_step_ids?.length || 0} ready steps, ${plan.blocked_step_ids?.length || 0} blockers, ${plan.segments?.length || 0} map segments loaded.`;
    }
    if (typeof payload === "string") {
      return payload.includes("Achievement & Collection Route Plan")
        ? "Markdown route export generated with assumptions and manual-planning boundaries."
        : "Route export generated.";
    }
    return "Achievement route planning output updated.";
  }
  if (target === "build") {
    if (data?.pack?.pack_id === "build_upgrade_effects") {
      return `${data.pack.rules?.length || 0} upgrade evidence rules available for reviewed import.`;
    }
    if (data?.result?.pack_id === "build_upgrade_effects") {
      return `${data.result.created_count || 0} disabled upgrade evidence rules imported. Enable reviewed rules before using them as evidence.`;
    }
    if (Array.isArray(data?.rules)) {
      const enabled = data.rules.filter((rule) => rule.enabled).length;
      return `${data.rules.length} build upgrade rules listed; ${enabled} enabled for reviewed evidence.`;
    }
    if (data?.rule) {
      return `${data.rule.name} enabled. Re-run Fit score to see reviewed KB evidence.`;
    }
    const fit = data?.fit?.score?.score;
    if (typeof fit === "number") {
      const upgradeCount = data.fit.upgrade_effects?.length || 0;
      return `Build fit score is ${Math.round(fit * 100)}%. ${upgradeCount} rune/sigil/relic effect checks need manual review before converting equipment.`;
    }
    if (data?.transition_plan) {
      return "Transition plan updated with reusable gear, missing gear, and manual budget guidance.";
    }
    return "Build workflow updated. Imported build ids are saved locally for this browser.";
  }
  if (target === "reports") {
    if (data?.job) {
      return "Report job created or loaded. Use the artifact id to open the exported report.";
    }
    if (data?.checkout) {
      return "Mock checkout completed for local entitlement testing.";
    }
    return "Report center updated. Products and pricing come from backend configuration.";
  }
  if (target === "freshness") {
    return "Freshness state refreshed. Stale data means recommendations need manual review.";
  }
  if (target === "privacy") {
    return "Privacy action completed. Recheck key status if you deleted private credentials.";
  }
  return "Output updated.";
}

function captureReportRefs(payload) {
  const job = payload?.data?.job || payload?.job;
  const artifactPath = job?.artifact_path || "";
  const artifactId =
    job?.artifact_id ||
    job?.artifact?.artifact_id ||
    job?.artifacts?.[0]?.artifact_id ||
    artifactPath.split(/[\\/]/).find((part) => part.startsWith("artifact_"));
  if (job?.job_id) {
    document.querySelector("#report-job-id").value = job.job_id;
    markStep("report", "Report job ready");
  }
  if (artifactId) {
    document.querySelector("#artifact-id").value = artifactId;
    markStep("report", "Artifact ready");
  }
  if (job?.job_id || artifactId) {
    addReportHistory({
      job_id: job?.job_id || "",
      artifact_id: artifactId || "",
      report_type: job?.report_type || "unknown",
      format: job?.format || "unknown",
      captured_at: new Date().toISOString(),
    });
  }
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadText(filename, text, type = "text/plain") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function debugBundleClientState() {
  return {
    active_view: readStorage(storageKeys.activeView),
    active_build_id: state.activeBuildId || readStorage(storageKeys.activeBuildId),
    player_intent: state.playerIntent || readStorage(storageKeys.playerIntent),
    report_history_count: reportHistory().length,
  };
}

function reportHistory() {
  const raw = readStorage(storageKeys.reportHistory, "[]");
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function addReportHistory(entry) {
  const history = [entry, ...reportHistory()].slice(0, 12);
  writeStorage(storageKeys.reportHistory, JSON.stringify(history));
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let payload = text;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = text;
  }
  if (!response.ok) {
    throw new Error(JSON.stringify({ status: response.status, payload }, null, 2));
  }
  return payload;
}

async function run(target, work) {
  render(target, "Loading...");
  renderSummary(target, "Working...");
  try {
    const result = await work();
    render(target, result);
    captureReportRefs(result);
    renderSummary(target, summarizeResult(target, result));
    return result;
  } catch (error) {
    render(target, `Request failed:\n${error.message}`);
    renderSummary(target, "The request failed. Check the JSON output for details and try the previous step again.");
    return null;
  }
}

function updateStatusFromKey(payload) {
  const status = document.querySelector("#account-status");
  const hasKey = Boolean(
    payload?.is_configured ??
      payload?.has_key ??
      payload?.data?.is_configured ??
      payload?.data?.has_key ??
      (payload?.status === "stored"),
  );
  status.textContent = hasKey ? "Account key stored" : "No API key stored";
  status.className = `status-pill ${hasKey ? "good" : "warn"}`;
  document.querySelector("#metric-connection").textContent = hasKey ? "Connected" : "Not connected";
  markStep("connect", hasKey ? "Key stored" : "No key stored", hasKey);
}

function renderDashboardPlan(plan) {
  renderActionList("#dashboard-today-actions", plan?.today_best_actions || []);
  renderActionList("#dashboard-week-actions", plan?.this_week_actions || []);
}

function renderPermissionReport(report) {
  const grid = document.querySelector("#permission-status-grid");
  if (!grid || !report) {
    return;
  }
  grid.innerHTML = "";
  const granted = new Set(report.granted_permissions || []);
  const permissionRows = [
    ...(report.required_permissions || []).map((permission) => ({ permission, type: "required" })),
    ...(report.optional_permissions || []).map((permission) => ({ permission, type: "optional" })),
  ];
  for (const row of permissionRows) {
    const status = granted.has(row.permission) ? "ready" : "limited";
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const label = document.createElement("span");
    item.className = `permission-status ${status}`;
    name.textContent = row.permission;
    label.textContent = status === "ready" ? "granted" : `missing ${row.type}`;
    item.append(name, label);
    grid.appendChild(item);
  }
  for (const impact of report.feature_impacts || []) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const label = document.createElement("span");
    item.className = `permission-status ${impact.status}`;
    name.textContent = impact.label;
    label.textContent = impact.status;
    item.append(name, label);
    item.title = impact.player_message || "";
    grid.appendChild(item);
  }
  renderValueReadiness(report);
}

function renderValueReadiness(report) {
  const summary = document.querySelector("#value-readiness-summary");
  const grid = document.querySelector("#value-module-grid");
  if (!summary || !grid || !report) {
    return;
  }
  const readiness = report.value_analysis_readiness || {};
  summary.textContent =
    readiness.player_message ||
    "Value analysis readiness is unknown until permissions are inspected.";
  grid.innerHTML = "";
  const modules = [
    ...(report.unlocked_analysis_modules || []),
    ...(report.blocked_analysis_modules || []),
  ];
  if (!modules.length) {
    grid.textContent = "No value-analysis module status is available yet.";
    return;
  }
  for (const module of modules) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const status = document.createElement("span");
    const detail = document.createElement("em");
    item.className = `value-module ${module.status || "blocked"}`;
    name.textContent = module.label || module.module_id;
    status.textContent = module.status || "unknown";
    detail.textContent = module.missing_permissions?.length
      ? `Missing: ${module.missing_permissions.join(", ")}`
      : "Unlocked";
    item.title = module.player_message || "";
    item.append(name, status, detail);
    grid.appendChild(item);
  }
}

function renderHoldingSummary(index) {
  const grid = document.querySelector("#holding-summary-grid");
  if (!grid || !index) {
    return;
  }
  const counts = index.location_counts || {};
  const rows = [
    ["Holdings", `${index.holding_count || 0} private summaries`],
    ["Wallet", `${counts.wallet || 0} entries`],
    ["Materials", `${counts.materials || 0} entries`],
    ["Bank", `${counts.bank || 0} entries`],
    ["Character gear", `${counts.character_equipment || 0} entries`],
    ["Coverage gaps", `${index.coverage_gaps?.length || 0}`],
  ];
  grid.innerHTML = "";
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    row.append(dt, dd);
    grid.appendChild(row);
  }
}

function renderAccountValueSummary(snapshot) {
  const grid = document.querySelector("#holding-summary-grid");
  if (!grid || !snapshot) {
    return;
  }
  const summary = snapshot.summary || {};
  const rows = [
    ["Buy value", formatCopper(summary.total_value_buy_copper || 0)],
    ["Net sell", formatCopper(summary.net_sell_value_copper || 0)],
    ["Priced", `${summary.priced_holding_count || 0}`],
    ["Unpriced", `${summary.unpriced_holding_count || 0}`],
    ["Account-bound", `${summary.account_bound_holding_count || 0}`],
    ["Price coverage", `${snapshot.diagnostics?.price_coverage_percent || 0}%`],
    ["Warnings", `${snapshot.warnings?.length || 0}`],
  ];
  grid.innerHTML = "";
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    row.append(dt, dd);
    grid.appendChild(row);
  }
  renderValueBreakdown("#value-location-breakdown", snapshot.by_location || [], "No location value yet.");
  renderValueBreakdown("#value-status-breakdown", snapshot.by_status || [], "No status coverage yet.");
  renderTopHoldings(snapshot.top_holdings || []);
  renderValueWarnings(snapshot.warnings || []);
  renderPriceRemediationSummary(snapshot);
  renderValueSourceInsights(snapshot.diagnostics?.source_insights || []);
  renderValueRemediationActions(snapshot.diagnostics?.remediation_actions || []);
}

function renderPlayerReadiness(readiness) {
  const label = document.querySelector("#player-readiness-label");
  const score = document.querySelector("#player-readiness-score");
  const count = document.querySelector("#player-readiness-check-count");
  const list = document.querySelector("#player-readiness-checks");
  if (!label || !score || !count || !list) {
    return;
  }
  label.textContent = readiness?.readiness_label || "unknown";
  score.textContent = typeof readiness?.readiness_score === "number" ? `${readiness.readiness_score}/100` : "--";
  count.textContent = `${readiness?.checks?.length || 0}`;
  list.innerHTML = "";
  const checks = readiness?.checks || [];
  if (!checks.length) {
    list.textContent = "No readiness checks are available yet.";
    return;
  }
  for (const check of checks) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const detail = document.createElement("span");
    item.className = `compact-list-row ${readinessCheckClass(check.status)}`;
    name.textContent = `${check.label || check.check_id}: ${check.status || "unknown"}`;
    detail.textContent = check.status === "ready" ? check.evidence || "" : `${check.evidence || ""} Next: ${check.next_action || ""}`;
    item.append(name, detail);
    list.appendChild(item);
  }
}

function renderPlayerReadinessHistory(history) {
  const list = document.querySelector("#player-readiness-history");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  const snapshots = history?.snapshots || [];
  const comparison = history?.comparison || {};
  const summary = document.createElement("div");
  const name = document.createElement("strong");
  const detail = document.createElement("span");
  summary.className = `compact-list-row ${comparison.status === "regressed" ? "warn" : "info"}`;
  name.textContent = comparison.summary || "Save at least two readiness snapshots before comparing changes.";
  detail.textContent = `${snapshots.length} snapshots, delta ${comparison.score_delta || 0}`;
  summary.append(name, detail);
  list.appendChild(summary);
  snapshots.slice(0, 5).forEach((snapshot) => {
    const item = document.createElement("div");
    const title = document.createElement("strong");
    const meta = document.createElement("span");
    item.className = "compact-list-row";
    title.textContent = `${snapshot.readiness_label || "unknown"} ${snapshot.readiness_score || 0}/100`;
    meta.textContent = `${snapshot.source || "player_dashboard"} - ${snapshot.created_at || snapshot.snapshot_id}`;
    item.append(title, meta);
    list.appendChild(item);
  });
}

function readinessCheckClass(status) {
  if (status === "ready") {
    return "info";
  }
  if (status === "blocked" || status === "needs_sync" || status === "needs_data" || status === "needs_price") {
    return "warn";
  }
  return "";
}

function formatCopper(value) {
  const copper = Math.max(0, Number(value) || 0);
  const gold = Math.floor(copper / 10000);
  const silver = Math.floor((copper % 10000) / 100);
  const coin = copper % 100;
  if (gold > 0) {
    return `${gold}g ${silver}s ${coin}c`;
  }
  if (silver > 0) {
    return `${silver}s ${coin}c`;
  }
  return `${coin}c`;
}

function renderValueBreakdown(selector, rows, emptyText) {
  const element = document.querySelector(selector);
  if (!element) {
    return;
  }
  element.innerHTML = "";
  if (!rows.length) {
    element.textContent = emptyText;
    return;
  }
  for (const row of rows.slice(0, 6)) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const detail = document.createElement("span");
    item.className = "compact-list-row";
    name.textContent = row.label || row.key;
    detail.textContent = `${formatCopper(row.value_buy_copper || 0)} / ${row.holding_count || 0} holdings`;
    item.append(name, detail);
    element.appendChild(item);
  }
}

function renderTopHoldings(holdings) {
  const element = document.querySelector("#value-top-holdings");
  if (!element) {
    return;
  }
  element.innerHTML = "";
  if (!holdings.length) {
    element.textContent = "No priced holdings yet. Add price snapshots or sync account data.";
    return;
  }
  for (const holding of holdings.slice(0, 8)) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const detail = document.createElement("span");
    item.className = "compact-list-row";
    name.textContent = holding.canonical_name || holding.entity_id;
    detail.textContent = `${formatCopper(holding.value_buy_copper || 0)} · ${holding.location_type || "unknown"} · ${holding.valuation_status || "unknown"}`;
    item.append(name, detail);
    element.appendChild(item);
  }
}

function renderValueWarnings(warnings) {
  const element = document.querySelector("#value-warning-list");
  if (!element) {
    return;
  }
  element.innerHTML = "";
  if (!warnings.length) {
    element.textContent = "No value warnings. Recheck after price or account sync changes.";
    return;
  }
  for (const warning of warnings.slice(0, 8)) {
    const item = document.createElement("div");
    const code = document.createElement("strong");
    const message = document.createElement("span");
    item.className = `compact-list-row ${warning.severity || "info"}`;
    code.textContent = warning.warning_code || "warning";
    message.textContent = remediationMessage(warning);
    item.append(code, message);
    element.appendChild(item);
  }
}

function renderPriceRemediationSummary(snapshot) {
  const element = document.querySelector("#price-remediation-summary");
  if (!element) {
    return;
  }
  const diagnostics = snapshot.diagnostics || {};
  const warnings = snapshot.warnings || [];
  const missing = warnings.filter((warning) => warning.warning_code === "missing_price").length;
  const stale = warnings.filter((warning) => warning.warning_code === "stale_price").length;
  const reserved = warnings.filter((warning) => warning.warning_code === "reserved_for_goal").length;
  if (!missing && !stale) {
    element.textContent = reserved
      ? `${reserved} holdings are reserved for active goals. Price coverage ${diagnostics.price_coverage_percent || 0}% has no missing or stale warnings.`
      : `Price coverage ${diagnostics.price_coverage_percent || 0}% has no missing or stale warnings.`;
    return;
  }
  const actions = [];
  if (missing) {
    actions.push(`${missing} missing prices: use Refresh official prices, then add manual snapshots for non-tradable or symbolic ids.`);
  }
  if (stale) {
    actions.push(`${stale} stale prices: refresh official prices before costly planning.`);
  }
  element.textContent = actions.join(" ");
}

function renderValueSourceInsights(insights) {
  const element = document.querySelector("#value-source-insights");
  if (!element) {
    return;
  }
  element.innerHTML = "";
  if (!insights.length) {
    element.textContent = "No source diagnostics yet. Sync account data and refresh dashboard.";
    return;
  }
  for (const insight of insights.slice(0, 6)) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const detail = document.createElement("span");
    item.className = `compact-list-row ${valueReadinessClass(insight.readiness_label)}`;
    name.textContent = `${insight.label || insight.key}: ${insight.readiness_label || "unknown"}`;
    detail.textContent = `${insight.price_coverage_percent || 0}% priced · ${formatCopper(insight.value_buy_copper || 0)} · ${insight.action_hint || ""}`;
    item.append(name, detail);
    element.appendChild(item);
  }
}

function renderValueRemediationActions(actions) {
  const element = document.querySelector("#value-remediation-actions");
  if (!element) {
    return;
  }
  element.innerHTML = "";
  if (!actions.length) {
    element.textContent = "No remediation actions yet. Refresh dashboard after account sync.";
    return;
  }
  for (const action of actions.slice(0, 5)) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const detail = document.createElement("span");
    item.className = `compact-list-row ${action.priority === "P0" || action.priority === "P1" ? "warn" : "info"}`;
    name.textContent = `${action.priority || "P3"} · ${action.label || action.action_id}`;
    detail.textContent = action.ui_action ? `${action.reason || ""} Action: ${action.ui_action}.` : action.reason || "";
    item.append(name, detail);
    element.appendChild(item);
  }
}

function renderAccountValueHistory(history) {
  const element = document.querySelector("#account-value-history");
  if (!element) {
    return;
  }
  element.innerHTML = "";
  const snapshots = history?.snapshots || [];
  const comparison = history?.comparison || {};
  const summary = document.createElement("div");
  const title = document.createElement("strong");
  const detail = document.createElement("span");
  summary.className = `compact-list-row ${comparison.status === "needs_review" ? "warn" : "info"}`;
  title.textContent = comparison.summary || "Save at least two account value snapshots before comparing changes.";
  detail.textContent = `${snapshots.length} snapshots, price coverage delta ${comparison.price_coverage_delta || 0}`;
  summary.append(title, detail);
  element.appendChild(summary);
  snapshots.slice(0, 5).forEach((snapshot) => {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const body = document.createElement("span");
    item.className = "compact-list-row";
    name.textContent = `${formatCopper(snapshot.total_value_buy_copper || 0)} · ${snapshot.freshness_label || "unknown"}`;
    body.textContent = `value ${snapshot.value_coverage_percent || 0}% / price ${snapshot.price_coverage_percent || 0}% - ${snapshot.created_at || snapshot.snapshot_id}`;
    item.append(name, body);
    element.appendChild(item);
  });
}

function renderPlayerHistoryCorrelation(correlation) {
  const status = document.querySelector("#history-correlation-status");
  const readinessDelta = document.querySelector("#history-correlation-readiness-delta");
  const priceDelta = document.querySelector("#history-correlation-price-delta");
  const list = document.querySelector("#history-correlation-list");
  if (!status || !readinessDelta || !priceDelta || !list) {
    return;
  }
  status.textContent = correlation?.status || "unknown";
  readinessDelta.textContent =
    typeof correlation?.readiness_score_delta === "number" ? `${correlation.readiness_score_delta}` : "--";
  priceDelta.textContent =
    typeof correlation?.price_coverage_delta === "number" ? `${correlation.price_coverage_delta}` : "--";
  list.innerHTML = "";
  const notes = correlation?.correlation_notes || [];
  const actions = correlation?.next_actions || [];
  if (!notes.length && !actions.length) {
    list.textContent = "No history correlation is available yet.";
    return;
  }
  notes.slice(0, 5).forEach((note) => {
    const item = document.createElement("div");
    const title = document.createElement("strong");
    const body = document.createElement("span");
    item.className = `compact-list-row ${correlation.status === "needs_review" ? "warn" : "info"}`;
    title.textContent = "Note";
    body.textContent = note;
    item.append(title, body);
    list.appendChild(item);
  });
  actions.slice(0, 4).forEach((action) => {
    const item = document.createElement("div");
    const title = document.createElement("strong");
    const body = document.createElement("span");
    item.className = "compact-list-row";
    title.textContent = "Next";
    body.textContent = action;
    item.append(title, body);
    list.appendChild(item);
  });
}

function renderPlayerSessionPacket(packet) {
  const schema = document.querySelector("#session-packet-schema");
  const evidenceCount = document.querySelector("#session-packet-evidence-count");
  const promptCount = document.querySelector("#session-packet-prompt-count");
  const list = document.querySelector("#session-packet-list");
  if (!schema || !evidenceCount || !promptCount || !list) {
    return;
  }
  schema.textContent = packet?.schema_version || "unknown";
  evidenceCount.textContent = `${packet?.debug_safe_evidence?.length || 0}`;
  promptCount.textContent = `${packet?.support_review_prompts?.length || 0}`;
  list.innerHTML = "";
  const rows = [
    ["Readiness", `${packet?.readiness_summary?.label || "unknown"} ${packet?.readiness_summary?.score || 0}/100`],
    ["Value", `price ${packet?.account_value_summary?.price_coverage_percent || 0}% / ${packet?.account_value_summary?.freshness_label || "unknown"}`],
    ["Correlation", packet?.history_correlation?.status || "unknown"],
  ];
  rows.forEach(([label, detail]) => appendCompactBridgeRow(list, label, detail, "info"));
  (packet?.support_review_prompts || []).slice(0, 4).forEach((prompt) => {
    appendCompactBridgeRow(list, "Support", prompt, "warn");
  });
}

function renderPlayerSessionPacketArtifacts(bundles) {
  const list = document.querySelector("#session-packet-artifacts");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  const items = Array.isArray(bundles) ? bundles : [];
  if (!items.length) {
    list.textContent = "No session packet files have been written yet.";
    return;
  }
  items.slice(0, 5).forEach((bundle) => {
    const item = document.createElement("div");
    const title = document.createElement("strong");
    const body = document.createElement("span");
    item.className = "compact-list-row info";
    title.textContent = `${bundle.artifact_id || "artifact"} · ${bundle.file_count || 0} files`;
    body.textContent = `checksum ${String(bundle.checksum_sha256 || "").slice(0, 12)} · manifest ${bundle.manifest_path || ""}`;
    item.append(title, body);
    list.appendChild(item);
  });
}

function renderPlayerSupportHandoff(handoff) {
  const list = document.querySelector("#support-handoff-summary");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  if (!handoff) {
    list.textContent = "No support handoff has been created yet.";
    return;
  }
  appendCompactBridgeRow(
    list,
    handoff.support_status || "unknown",
    `${handoff.handoff_id || "handoff"} · checksum ${String(handoff.session_artifact_bundle?.checksum_sha256 || "").slice(0, 12)}`,
    handoff.support_status === "ready" ? "info" : "warn"
  );
  appendCompactBridgeRow(
    list,
    "Debug review",
    handoff.debug_bundle_review?.overall_status || "unknown",
    handoff.debug_bundle_review?.overall_status === "ready" ? "info" : "warn"
  );
  (handoff.recommended_next_actions || []).slice(0, 4).forEach((action) => {
    appendCompactBridgeRow(list, "Next", action, "warn");
  });
}

function renderPlayerSupportHandoffArtifacts(bundles) {
  const list = document.querySelector("#support-handoff-artifacts");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  const items = Array.isArray(bundles) ? bundles : [];
  if (!items.length) {
    list.textContent = "No support handoff files have been written yet.";
    return;
  }
  items.slice(0, 5).forEach((bundle) => {
    const item = document.createElement("div");
    const title = document.createElement("strong");
    const body = document.createElement("span");
    item.className = `compact-list-row ${bundle.support_status === "ready" ? "info" : "warn"}`;
    title.textContent = `${bundle.artifact_id || "handoff"} · ${bundle.file_count || 0} files`;
    body.textContent = `status ${bundle.support_status || "unknown"} · checksum ${String(bundle.checksum_sha256 || "").slice(0, 12)}`;
    item.append(title, body);
    list.appendChild(item);
  });
}

function renderPlayerSupportHandoffZipVerification(verification) {
  const list = document.querySelector("#support-handoff-zip-status");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  if (!verification) {
    list.textContent = "No support handoff zip verification has run yet.";
    return;
  }
  appendCompactBridgeRow(
    list,
    verification.ready ? "ready" : "blocked",
    `${verification.file_count || 0} files · checksum ${String(verification.checksum_sha256 || "").slice(0, 12)}`,
    verification.ready ? "info" : "warn"
  );
  (verification.blockers || []).slice(0, 4).forEach((blocker) => {
    appendCompactBridgeRow(list, "Blocker", blocker, "warn");
  });
  (verification.warnings || []).slice(0, 3).forEach((warning) => {
    appendCompactBridgeRow(list, "Warning", warning, "warn");
  });
}

function valueReadinessClass(label) {
  if (label === "ready") {
    return "info";
  }
  if (label === "partial" || label === "needs_price") {
    return "warn";
  }
  return "";
}

function renderAccountValueEvidenceBridge(selector, bridge) {
  const element = document.querySelector(selector);
  if (!element) {
    return;
  }
  element.innerHTML = "";
  if (!bridge) {
    element.textContent = "No account value evidence bridge is available yet.";
    return;
  }
  const rows = [
    ["Coverage", `value ${bridge.value_coverage_percent || 0}% / price ${bridge.price_coverage_percent || 0}% / ${bridge.freshness_label || "unknown"}`],
    ["Do-not-sell", `${bridge.do_not_sell_note_count || 0} reserved holdings / ${bridge.warning_count || 0} warnings`],
  ];
  for (const [label, detail] of rows) {
    appendCompactBridgeRow(element, label, detail, "info");
  }
  for (const source of (bridge.source_summary || []).slice(0, 3)) {
    appendCompactBridgeRow(element, "Source", source, "");
  }
  for (const action of (bridge.remediation_summary || []).slice(0, 3)) {
    appendCompactBridgeRow(element, "Action", action, "warn");
  }
}

function appendCompactBridgeRow(element, label, detail, className) {
  const item = document.createElement("div");
  const name = document.createElement("strong");
  const body = document.createElement("span");
  item.className = `compact-list-row ${className || ""}`;
  name.textContent = label;
  body.textContent = detail;
  item.append(name, body);
  element.appendChild(item);
}

function remediationMessage(warning) {
  const message = warning.player_message || "";
  if (warning.warning_code === "missing_price") {
    return `${message} Action: refresh official prices or add a manual price snapshot if this item is not official-commerce priced.`;
  }
  if (warning.warning_code === "stale_price") {
    return `${message} Action: refresh official prices before relying on this value.`;
  }
  return message;
}

function renderSyncProgress(progress) {
  if (!Array.isArray(progress)) {
    return;
  }
  const idByEndpoint = {
    "/v2/account": "sync-profile",
    "/v2/characters": "sync-characters",
    "/v2/account/wallet": "sync-wallet",
    "/v2/account/materials": "sync-materials",
    "/v2/account/bank": "sync-bank",
    "/v2/account/inventory": "sync-shared-inventory",
    "/v2/account/achievements": "sync-achievements",
    "/v2/commerce/transactions/current/buys": "sync-tradingpost-buys",
    "/v2/commerce/transactions/current/sells": "sync-tradingpost-sells",
  };
  for (const item of progress) {
    const element = document.querySelector(`#${idByEndpoint[item.endpoint]}`);
    if (!element) {
      continue;
    }
    const status = item.status || "not_started";
    element.textContent = `${item.label}: ${status}`;
    element.className = "";
    if (["succeeded", "queued", "syncing"].includes(status)) {
      element.classList.add("ready");
    }
    if (["delayed", "needs_review", "blocked"].includes(status)) {
      element.classList.add(status);
    }
    element.title = item.player_message || "";
  }
}

function updateStatusFromSync(payload) {
  const status = document.querySelector("#sync-status");
  const label = payload?.status || payload?.queue_status || "Sync status updated";
  const goodStatuses = new Set(["ok", "queued", "succeeded"]);
  const warnStatuses = new Set(["idle", "not_started", "delayed", "refresh_pending", "retry_scheduled"]);
  status.textContent = String(label);
  status.className = `status-pill ${goodStatuses.has(label) ? "good" : warnStatuses.has(label) ? "warn" : "muted"}`;
  document.querySelector("#metric-sync").textContent = new Date().toLocaleString();
  document.querySelector("#freshness-account").textContent = "Checked just now";
  const freshnessCard = document.querySelector("#freshness-account-card");
  if (freshnessCard) {
    freshnessCard.textContent = `Account sync state checked: ${label}`;
  }
  renderSyncProgress(payload?.endpoint_progress || payload?.data?.endpoint_progress || []);
  markStep("sync", String(label));
}

function renderConnectionDiagnostic(report) {
  const grid = document.querySelector("#connection-diagnostic-grid");
  if (!grid || !report) {
    return;
  }
  grid.innerHTML = "";
  for (const check of report.checks || []) {
    const item = document.createElement("div");
    const name = document.createElement("strong");
    const status = document.createElement("span");
    const message = document.createElement("span");
    const details = document.createElement("span");
    item.className = `diagnostic-check ${check.status}`;
    name.textContent = check.label;
    status.textContent = check.severity && check.severity !== "none" ? `${check.status} / ${check.severity}` : check.status;
    message.textContent = check.player_message || "";
    details.textContent = diagnosticDetailsText(check.details || {});
    item.title = check.player_message || "";
    item.append(name, status, message);
    if (details.textContent) {
      item.appendChild(details);
    }
    if (check.fix_action_id && check.fix_label) {
      const fixButton = document.createElement("button");
      fixButton.type = "button";
      fixButton.className = "diagnostic-fix";
      fixButton.textContent = check.fix_label;
      fixButton.dataset.fixAction = check.fix_action_id;
      fixButton.addEventListener("click", (event) => {
        event.preventDefault();
        runDiagnosticFix(check.fix_action_id);
      });
      item.appendChild(fixButton);
    }
    grid.appendChild(item);
  }
}

function diagnosticDetailsText(details) {
  const parts = [];
  if (details.missing_required_permissions?.length) {
    parts.push(`Missing: ${details.missing_required_permissions.join(", ")}`);
  }
  if (typeof details.private_player_state_count === "number") {
    parts.push(`Private records: ${details.private_player_state_count}`);
  }
  if (typeof details.synced_character_snapshot_count === "number") {
    parts.push(`Synced snapshots: ${details.synced_character_snapshot_count}`);
  }
  if (typeof details.synced_gear_count === "number") {
    parts.push(`Synced gear: ${details.synced_gear_count}`);
  }
  return parts.join(" | ");
}

function runDiagnosticFix(actionId) {
  if (actionId === "focus_api_key_input") {
    document.querySelector("#api-key-input")?.focus();
    renderSummary("connect", "Paste or update a GW2 API key with account, characters, inventories, wallet, and progression permissions.");
    return;
  }
  if (actionId === "loadCharacterSnapshots") {
    showView("build");
  }
  const action = actions[actionId];
  if (action) {
    action();
  }
}

function getNumber(selector) {
  return Number(document.querySelector(selector).value || 0);
}

function routeList(selector) {
  return document
    .querySelector(selector)
    .value.split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function routeRequestPayload() {
  return {
    user_id: "local-user",
    goal_id: document.querySelector("#route-goal").value,
    available_minutes: getNumber("#route-minutes") || 45,
    completed_step_ids: routeList("#route-completed"),
    unlocked_prerequisite_ids: routeList("#route-prereqs"),
    include_group_content: document.querySelector("#route-include-group").checked,
  };
}

function routeOfficialAchievementIds() {
  return routeList("#route-official-achievement-ids")
    .map((item) => Number(item))
    .filter((item) => Number.isInteger(item) && item > 0);
}

function routeOfficialFetchPreviewPayload() {
  const achievementIds = routeOfficialAchievementIds();
  if (!achievementIds.length) {
    throw new Error("Add at least one official achievement id before fetching a preview.");
  }
  return {
    source_id: "official:achievement-route-fetch-preview:player-ui",
    title: "Player UI official achievement fetch preview",
    goal_id: document.querySelector("#route-goal").value,
    reviewed_by: document.querySelector("#route-reviewer").value || "player_ui_operator",
    achievement_ids: achievementIds,
    account_achievements: [],
    use_stored_account_progress: false,
  };
}

function routeReviewPayload() {
  const reviewer = document.querySelector("#route-reviewer").value.trim();
  if (!reviewer) {
    throw new Error("Reviewer is required before promoting a route source.");
  }
  return {
    confirmed_reviewed: true,
    reviewer,
    reviewed_source_id: document.querySelector("#route-reviewed-source-id").value.trim() || null,
    review_notes: routeList("#route-review-notes"),
  };
}

function renderRoutePlan(plan) {
  document.querySelector("#route-ready-count").textContent = String(plan?.ready_step_ids?.length || 0);
  document.querySelector("#route-blocked-count").textContent = String(plan?.blocked_step_ids?.length || 0);
  document.querySelector("#route-gated-count").textContent = String(plan?.time_gated_step_ids?.length || 0);
  document.querySelector("#route-segment-count").textContent = String(plan?.segments?.length || 0);
  document.querySelector("#route-source-count").textContent = String(plan?.source_ids?.length || 0);
  renderActionList("#route-next-actions", plan?.next_actions || []);
}

function renderRouteFetchPreview(fetchPreview) {
  document.querySelector("#route-fetch-count").textContent = String(fetchPreview?.fetched_achievement_ids?.length || 0);
  document.querySelector("#route-missing-count").textContent = String(fetchPreview?.missing_achievement_ids?.length || 0);
}

function renderRoutePromotion(promotion) {
  const sourceId = promotion?.manifest?.source_id || "";
  state.lastRoutePromotionSourceId = sourceId;
  document.querySelector("#route-promoted-count").textContent = String(promotion?.manifest?.steps?.length || 0);
  if (sourceId) {
    document.querySelector("#route-reviewed-source-id").value = sourceId;
  }
}

function renderRoutePromotionAudit(audit) {
  document.querySelector("#route-audit-count").textContent = String(audit?.records?.length || 0);
}

function renderRouteReleaseReadiness(readiness) {
  const label = readiness?.maturity_label || "unknown";
  const score = typeof readiness?.readiness_score === "number" ? readiness.readiness_score : "--";
  document.querySelector("#route-readiness-score").textContent = `${label} ${score}/100`;
}

function renderRouteSourceQuality(quality) {
  const label = quality?.maturity_label || "unknown";
  const score = typeof quality?.overall_score === "number" ? quality.overall_score : "--";
  document.querySelector("#route-quality-score").textContent = `${label} ${score}/100`;
}

function renderRouteRemediationQueue(queue) {
  const open = typeof queue?.open_item_count === "number" ? queue.open_item_count : "--";
  const p0 = typeof queue?.p0_count === "number" ? queue.p0_count : "--";
  state.lastRouteRemediationItemId = queue?.items?.[0]?.item_id || "";
  document.querySelector("#route-remediation-count").textContent = `${open} open / ${p0} P0`;
}

function renderRouteRemediationReviewAudit(audit) {
  document.querySelector("#route-audit-count").textContent = String(audit?.records?.length || 0);
}

function renderRouteRemediationReadiness(readiness) {
  const label = readiness?.maturity_label || "unknown";
  const score = typeof readiness?.readiness_score === "number" ? readiness.readiness_score : "--";
  document.querySelector("#route-remediation-readiness-score").textContent = `${label} ${score}/100`;
}

function renderRouteBackfillCandidates(exportPayload) {
  const candidate = exportPayload?.candidates?.find((item) => item.step_id) || exportPayload?.candidates?.[0] || {};
  state.lastRouteBackfillCandidateId = candidate.candidate_id || "";
  const count = typeof exportPayload?.candidate_count === "number" ? exportPayload.candidate_count : "--";
  document.querySelector("#route-backfill-count").textContent = String(count);
}

function renderRouteBackfillCandidateReviewAudit(audit) {
  document.querySelector("#route-backfill-audit-count").textContent = String(audit?.records?.length || 0);
}

function renderRouteBackfillCandidateReadiness(readiness) {
  const label = readiness?.maturity_label || "unknown";
  const score = typeof readiness?.readiness_score === "number" ? readiness.readiness_score : "--";
  document.querySelector("#route-backfill-readiness-score").textContent = `${label} ${score}/100`;
}

function renderRouteSourceEditPatchDraft(exportPayload) {
  state.lastRouteSourcePatchDraftId = exportPayload?.drafts?.[0]?.draft_id || "";
  const drafts = typeof exportPayload?.draft_count === "number" ? exportPayload.draft_count : "--";
  const operations = typeof exportPayload?.operation_count === "number" ? exportPayload.operation_count : "--";
  document.querySelector("#route-source-patch-draft-count").textContent = `${drafts} drafts / ${operations} ops`;
}

function renderRouteSourceEditPatchApplyAudit(audit) {
  document.querySelector("#route-source-patch-apply-count").textContent = String(audit?.records?.length || 0);
}

function renderRouteDraftSourcePromotionAudit(audit) {
  document.querySelector("#route-draft-source-promotion-count").textContent = String(audit?.records?.length || 0);
}

function renderRouteReleaseEvidenceBundle(bundle) {
  const label = bundle?.maturity_label || "unknown";
  const sources = typeof bundle?.reviewed_source_count === "number" ? bundle.reviewed_source_count : "--";
  const blockers = typeof bundle?.blocker_count === "number" ? bundle.blocker_count : "--";
  document.querySelector("#route-release-evidence-count").textContent = `${label} / ${sources} sources / ${blockers} blockers`;
}

function renderRouteReleaseEvidenceArchive(indexOrRecord) {
  const records = Array.isArray(indexOrRecord?.records) ? indexOrRecord.records : null;
  const count = records ? indexOrRecord.total_records : 1;
  const latest = records ? indexOrRecord.latest_archive_id : indexOrRecord?.archive_id;
  document.querySelector("#route-release-evidence-archive-count").textContent = `${count || 0} archived / ${latest || "--"}`;
}

function renderRouteReleaseEvidenceArchiveDiff(diff) {
  const label = diff?.maturity_label || "unknown";
  const regressions = typeof diff?.regression_count === "number" ? diff.regression_count : "--";
  const improvements = typeof diff?.improvement_count === "number" ? diff.improvement_count : "--";
  document.querySelector("#route-release-evidence-diff-count").textContent = `${label} / ${regressions} regressions / ${improvements} improvements`;
}

function renderRouteReleaseSignoff(recordOrAudit) {
  const records = Array.isArray(recordOrAudit?.records) ? recordOrAudit.records : null;
  const latest = records ? records[0] : recordOrAudit;
  const count = records ? records.length : latest?.signoff_id ? 1 : 0;
  const status = latest?.status || "unknown";
  document.querySelector("#route-release-signoff-count").textContent = `${status} / ${count} records`;
}

function renderRouteOperatorReleaseDashboard(dashboard) {
  const label = dashboard?.maturity_label || "unknown";
  const blockers = Array.isArray(dashboard?.blockers) ? dashboard.blockers.length : "--";
  const missing = Array.isArray(dashboard?.missing_gates) ? dashboard.missing_gates.length : "--";
  document.querySelector("#route-release-dashboard-count").textContent = `${label} / ${blockers} blockers / ${missing} missing`;
}

function renderRouteReleaseExportPacket(packet) {
  const label = packet?.maturity_label || "unknown";
  const artifacts = typeof packet?.artifact_count === "number" ? packet.artifact_count : "--";
  document.querySelector("#route-release-export-packet-count").textContent = `${label} / ${artifacts} artifacts`;
}

function renderRouteReleaseExportArtifacts(index) {
  const count = typeof index?.file_count === "number" ? index.file_count : "--";
  const packet = index?.packet_id || "--";
  state.lastRouteReleaseExportArtifactPath = index?.files?.[0]?.relative_path || "";
  document.querySelector("#route-release-export-artifact-count").textContent = `${count} files / ${packet}`;
}

function renderRouteReleaseExportBundle(bundle) {
  const count = typeof bundle?.file_count === "number" ? bundle.file_count : "--";
  const checksum = bundle?.checksum_sha256 ? bundle.checksum_sha256.slice(0, 12) : "--";
  document.querySelector("#route-release-export-bundle-count").textContent = `${count} files / ${checksum}`;
}

function renderRouteReleaseExportBundleVerification(verification) {
  const status = verification?.ready ? "ready" : "blocked";
  const blockers = Array.isArray(verification?.blockers) ? verification.blockers.length : "--";
  document.querySelector("#route-release-export-bundle-verification-count").textContent = `${status} / ${blockers} blockers`;
}

function renderRouteReleaseExportBundleVerificationAudit(audit) {
  const count = Array.isArray(audit?.records) ? audit.records.length : "--";
  const latest = audit?.records?.[0];
  const status = latest ? (latest.ready ? "ready" : "blocked") : "--";
  document.querySelector("#route-release-export-bundle-audit-count").textContent = `${count} records / ${status}`;
}

function renderRouteOperatorHandoffChecklist(checklist) {
  const label = checklist?.maturity_label || "--";
  const missing = Array.isArray(checklist?.missing_gates) ? checklist.missing_gates.length : "--";
  document.querySelector("#route-operator-handoff-count").textContent = `${label} / ${missing} missing`;
}

function renderRouteFinalReleaseArtifact(selector, artifact) {
  const label = artifact?.maturity_label || "--";
  const ready = typeof artifact?.ready === "boolean" ? (artifact.ready ? "ready" : "blocked") : "--";
  document.querySelector(selector).textContent = `${label} / ${ready}`;
}

function renderRouteOperatorActionBundle(bundle) {
  renderRouteSourceQuality(bundle?.quality || {});
  renderRouteRemediationQueue(bundle?.remediation_queue || {});
  renderRouteRemediationReviewAudit(bundle?.remediation_review_audit || {});
  renderRouteRemediationReadiness(bundle?.remediation_readiness || {});
  renderRouteReleaseReadiness(bundle?.release_readiness || {});
}

function buildImportPayload() {
  const estimatedCost = getNumber("#build-cost");
  return {
    name: document.querySelector("#build-name").value,
    source: {
      name: "manual_player_ui",
      url: null,
      attribution: "User-provided structured build data from GW2Radar Player UI.",
    },
    profession: document.querySelector("#build-profession").value,
    specialization: document.querySelector("#build-spec").value,
    role: document.querySelector("#build-role").value,
    game_mode: document.querySelector("#build-mode").value,
    patch_version: null,
    patch_freshness_days: getNumber("#build-freshness"),
    difficulty: "medium",
    estimated_transition_cost_gold: estimatedCost,
    requirements: [
      {
        slot: "chest",
        item_name: "Ascended Chest",
        stat_combo: "Berserker",
        required: true,
        estimated_cost_gold: Math.max(estimatedCost * 0.35, 1),
      },
      {
        slot: "weapon_1",
        item_name: "Primary Weapon",
        stat_combo: "Berserker",
        required: true,
        estimated_cost_gold: Math.max(estimatedCost * 0.45, 1),
      },
      {
        slot: "relic",
        item_name: "Relic",
        stat_combo: "Power",
        required: false,
        estimated_cost_gold: Math.max(estimatedCost * 0.2, 0),
      },
    ],
  };
}

function accountGearPayload() {
  if (state.selectedAccountGear) {
    return {
      ...state.selectedAccountGear,
      wallet_gold: getNumber("#wallet-gold") || state.selectedAccountGear.wallet_gold || 0,
    };
  }
  return {
    profession: document.querySelector("#build-profession").value,
    specializations: [document.querySelector("#build-spec").value],
    preferred_game_modes: [document.querySelector("#build-mode").value],
    difficulty_preference: "medium",
    wallet_gold: getNumber("#wallet-gold"),
    gear: [
      {
        slot: "chest",
        item_name: "Owned Chest",
        stat_combo: document.querySelector("#owned-stat").value,
      },
    ],
  };
}

function renderCharacterSnapshots(snapshots) {
  const select = document.querySelector("#character-snapshot");
  select.innerHTML = '<option value="">Manual fields only</option>';
  for (const snapshot of snapshots) {
    const option = document.createElement("option");
    option.value = snapshot.snapshot_id;
    const source = snapshot.source === "synced_official_api" ? "synced" : "manual";
    option.textContent = `${snapshot.character_name} (${snapshot.profession} / ${snapshot.specialization}) - ${source}`;
    select.appendChild(option);
  }
}

function renderLegendaryGoalCatalog(goals) {
  const select = document.querySelector("#legendary-goal");
  if (!select || !Array.isArray(goals)) {
    return;
  }
  select.innerHTML = "";
  for (const goal of goals) {
    const option = document.createElement("option");
    option.value = goal.graph_goal_id;
    option.textContent = `${goal.display_name} (${goal.goal_type})`;
    select.appendChild(option);
  }
}

function renderFreshnessAnnotations(annotations) {
  const grid = document.querySelector("#freshness-annotation-grid");
  if (!grid || !Array.isArray(annotations)) {
    return;
  }
  grid.innerHTML = "";
  for (const annotation of annotations) {
    const card = document.createElement("article");
    const title = document.createElement("strong");
    const status = document.createElement("span");
    const message = document.createElement("span");
    const refresh = document.createElement("span");
    card.className = "freshness-annotation";
    title.textContent = `${annotation.subject}: ${annotation.status}`;
    status.textContent = `Confidence: ${annotation.source_confidence}`;
    message.textContent = annotation.player_message;
    refresh.textContent = `Refresh: ${annotation.next_refresh_action}`;
    card.append(title, status, message, refresh);
    grid.appendChild(card);
  }
}

function renderBuildUpgradeRules(rules) {
  const select = document.querySelector("#build-upgrade-rule-id");
  const status = document.querySelector("#build-rule-pack-status");
  if (!select || !status || !Array.isArray(rules)) {
    return;
  }
  state.buildUpgradeRules = rules;
  select.innerHTML = '<option value="">Select disabled reviewed rule</option>';
  let enabledCount = 0;
  let disabledCount = 0;
  for (const rule of rules) {
    if (rule.enabled) {
      enabledCount += 1;
    } else {
      disabledCount += 1;
    }
    const option = document.createElement("option");
    option.value = rule.rule_id || "";
    option.disabled = Boolean(rule.enabled || !rule.rule_id);
    option.textContent = `${rule.enabled ? "enabled" : "disabled"} - ${rule.name}`;
    select.appendChild(option);
  }
  status.textContent = `${rules.length} rules: ${enabledCount} enabled, ${disabledCount} disabled.`;
}

function applyAccountGearSnapshot(snapshot, accountGear) {
  state.selectedAccountGear = accountGear;
  document.querySelector("#build-profession").value = accountGear.profession || "";
  document.querySelector("#build-spec").value = accountGear.specializations?.[0] || "";
  document.querySelector("#build-mode").value = accountGear.preferred_game_modes?.[0] || "";
  document.querySelector("#wallet-gold").value = accountGear.wallet_gold || 0;
  const gearCount = accountGear.gear?.length || 0;
  const source = snapshot.source === "synced_official_api" ? "Official API synced snapshot" : "Manual sample snapshot";
  document.querySelector("#gear-summary").textContent =
    `${snapshot.character_name}: ${gearCount} gear slots loaded. ${source}. ${snapshot.assumptions?.[0] || "Verify manually."}`;
}

function updateReturnerScores(report) {
  const idMap = {
    travel: "travel",
    combat: "combat",
    progression: "progression",
    legendary: "legendary",
    group_pve: "group-pve",
  };
  for (const dimension of report.dimensions || []) {
    const uiId = idMap[dimension.dimension_id];
    if (!uiId) {
      continue;
    }
    const score = document.querySelector(`#score-${uiId}`);
    const status = document.querySelector(`#status-${uiId}`);
    if (score) {
      score.textContent = String(dimension.score);
    }
    if (status) {
      status.textContent = dimension.status;
    }
  }
}

function activeBuildId() {
  return document.querySelector("#active-build-id").value || state.activeBuildId;
}

function requireActiveBuildId() {
  const buildId = activeBuildId();
  if (!buildId) {
    throw new Error("Import or select a build before running this action.");
  }
  return buildId;
}

const actions = {
  startWithDashboard: () => {
    showView("dashboard");
    renderSummary("welcome", "Dashboard opened. Connect and sync if this is your first session.");
  },
  selectIntent: (intent) => {
    state.playerIntent = intent;
    writeStorage(storageKeys.playerIntent, intent);
    renderSummary("welcome", `Selected intent: ${intent}.`);
    markStep("plan", `Intent: ${intent}`);
  },
  refreshDashboard: () =>
    run("dashboard", async () => {
      const key = await fetchJson("/account/api-key/status");
      updateStatusFromKey(key);
      const sync = await fetchJson("/api/v1/account/sync/status");
      updateStatusFromSync(sync);
      const dashboard = await fetchJson("/api/v1/player/dashboard");
      renderDashboardPlan(dashboard?.data?.dashboard || {});
      renderFreshnessAnnotations(dashboard?.data?.dashboard?.data_freshness || []);
      const holdings = await fetchJson("/api/v1/player/account-holdings?include_holdings=false");
      renderHoldingSummary(holdings?.data?.account_holding_index || {});
      const value = await fetchJson("/api/v1/player/account-value");
      renderAccountValueSummary(value?.data?.account_value_snapshot || {});
      const readiness = await fetchJson("/api/v1/player/readiness");
      renderPlayerReadiness(readiness?.data?.readiness || {});
      const correlation = await fetchJson("/api/v1/player/history/correlation?limit=10");
      renderPlayerHistoryCorrelation(correlation?.data?.correlation || {});
      const sessionPacket = await fetchJson("/api/v1/player/session-packet?limit=10");
      renderPlayerSessionPacket(sessionPacket?.data?.session_packet || {});
      return { account: key, sync, dashboard, holdings, value, readiness, correlation, sessionPacket };
    }),
  playerReadiness: () =>
    run("dashboard", async () => {
      const sync = await fetchJson("/api/v1/account/sync/status");
      updateStatusFromSync(sync);
      const value = await fetchJson("/api/v1/player/account-value");
      renderAccountValueSummary(value?.data?.account_value_snapshot || {});
      const readiness = await fetchJson("/api/v1/player/readiness");
      renderPlayerReadiness(readiness?.data?.readiness || {});
      return { sync, value, readiness };
    }),
  exportPlayerReadinessMarkdown: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/readiness?format=markdown").then((response) => response.text());
      downloadText("gw2radar-player-readiness.md", text, "text/markdown");
      return text;
    }),
  exportPlayerReadinessCsv: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/readiness?format=csv").then((response) => response.text());
      downloadText("gw2radar-player-readiness.csv", text, "text/csv");
      return text;
    }),
  savePlayerReadinessSnapshot: () =>
    run("dashboard", async () => {
      const saved = await fetchJson("/api/v1/player/readiness/history?source=player_dashboard", { method: "POST" });
      const history = await fetchJson("/api/v1/player/readiness/history?limit=10");
      renderPlayerReadinessHistory(history?.data?.history || {});
      return { saved, history };
    }),
  loadPlayerReadinessHistory: () =>
    run("dashboard", async () => {
      const history = await fetchJson("/api/v1/player/readiness/history?limit=10");
      renderPlayerReadinessHistory(history?.data?.history || {});
      return history;
    }),
  exportPlayerReadinessHistoryMarkdown: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/readiness/history?format=markdown&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-player-readiness-history.md", text, "text/markdown");
      return text;
    }),
  exportPlayerReadinessHistoryCsv: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/readiness/history?format=csv&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-player-readiness-history.csv", text, "text/csv");
      return text;
    }),
  loadPlayerHistoryCorrelation: () =>
    run("dashboard", async () => {
      const correlation = await fetchJson("/api/v1/player/history/correlation?limit=10");
      renderPlayerHistoryCorrelation(correlation?.data?.correlation || {});
      return correlation;
    }),
  exportPlayerHistoryCorrelationMarkdown: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/history/correlation?format=markdown&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-player-history-correlation.md", text, "text/markdown");
      return text;
    }),
  exportPlayerHistoryCorrelationCsv: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/history/correlation?format=csv&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-player-history-correlation.csv", text, "text/csv");
      return text;
    }),
  loadPlayerSessionPacket: () =>
    run("dashboard", async () => {
      const packet = await fetchJson("/api/v1/player/session-packet?limit=10");
      renderPlayerSessionPacket(packet?.data?.session_packet || {});
      return packet;
    }),
  exportPlayerSessionPacketMarkdown: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/session-packet?format=markdown&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-player-session-packet.md", text, "text/markdown");
      return text;
    }),
  exportPlayerSessionPacketCsv: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/session-packet?format=csv&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-player-session-packet.csv", text, "text/csv");
      return text;
    }),
  writePlayerSessionPacketArtifacts: () =>
    run("dashboard", async () => {
      const payload = await fetchJson("/api/v1/player/session-packet/artifacts?limit=10", { method: "POST" });
      const bundles = await fetchJson("/api/v1/player/session-packet/artifacts?limit=10");
      renderPlayerSessionPacketArtifacts(bundles?.data?.artifact_bundles || []);
      return { payload, bundles };
    }),
  loadPlayerSessionPacketArtifacts: () =>
    run("dashboard", async () => {
      const bundles = await fetchJson("/api/v1/player/session-packet/artifacts?limit=10");
      renderPlayerSessionPacketArtifacts(bundles?.data?.artifact_bundles || []);
      return bundles;
    }),
  createPlayerSupportHandoff: () =>
    run("dashboard", async () => {
      const debugBundle = await fetchJson("/account/debug-bundle", {
        method: "POST",
        body: JSON.stringify(debugBundleClientState()),
      });
      const handoff = await fetchJson("/api/v1/player/support-handoff?limit=10", {
        method: "POST",
        body: JSON.stringify({ debug_bundle: debugBundle }),
      });
      renderPlayerSupportHandoff(handoff?.data?.support_handoff || null);
      const bundles = await fetchJson("/api/v1/player/session-packet/artifacts?limit=10");
      renderPlayerSessionPacketArtifacts(bundles?.data?.artifact_bundles || []);
      return { handoff, bundles };
    }),
  writePlayerSupportHandoffArtifacts: () =>
    run("dashboard", async () => {
      const debugBundle = await fetchJson("/account/debug-bundle", {
        method: "POST",
        body: JSON.stringify(debugBundleClientState()),
      });
      const payload = await fetchJson("/api/v1/player/support-handoff/artifacts?limit=10", {
        method: "POST",
        body: JSON.stringify({ debug_bundle: debugBundle }),
      });
      const bundles = await fetchJson("/api/v1/player/support-handoff/artifacts?limit=10");
      renderPlayerSupportHandoffArtifacts(bundles?.data?.artifact_bundles || []);
      return { payload, bundles };
    }),
  loadPlayerSupportHandoffArtifacts: () =>
    run("dashboard", async () => {
      const bundles = await fetchJson("/api/v1/player/support-handoff/artifacts?limit=10");
      renderPlayerSupportHandoffArtifacts(bundles?.data?.artifact_bundles || []);
      return bundles;
    }),
  downloadPlayerSupportHandoffZip: () =>
    run("dashboard", async () => {
      const response = await fetch("/api/v1/player/support-handoff/artifacts/bundle");
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "gw2radar-player-support-handoff.zip";
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      return {
        filename,
        checksum_sha256: response.headers.get("x-checksum-sha256"),
        size_bytes: blob.size,
      };
    }),
  verifyPlayerSupportHandoffZip: () =>
    run("dashboard", async () => {
      const payload = await fetchJson("/api/v1/player/support-handoff/artifacts/bundle/verify", { method: "POST" });
      renderPlayerSupportHandoffZipVerification(payload?.data?.support_handoff_zip_verification || {});
      return payload;
    }),
  exportAccountValueMarkdown: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/account-value?format=markdown").then((response) => response.text());
      downloadText("gw2radar-account-value.md", text, "text/markdown");
      return text;
    }),
  exportAccountValueCsv: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/account-value?format=csv").then((response) => response.text());
      downloadText("gw2radar-account-value.csv", text, "text/csv");
      return text;
    }),
  saveAccountValueSnapshot: () =>
    run("dashboard", async () => {
      const saved = await fetchJson("/api/v1/player/account-value/history?source=player_dashboard", { method: "POST" });
      const history = await fetchJson("/api/v1/player/account-value/history?limit=10");
      renderAccountValueHistory(history?.data?.history || {});
      return { saved, history };
    }),
  loadAccountValueHistory: () =>
    run("dashboard", async () => {
      const history = await fetchJson("/api/v1/player/account-value/history?limit=10");
      renderAccountValueHistory(history?.data?.history || {});
      return history;
    }),
  exportAccountValueHistoryMarkdown: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/account-value/history?format=markdown&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-account-value-history.md", text, "text/markdown");
      return text;
    }),
  exportAccountValueHistoryCsv: () =>
    run("dashboard", async () => {
      const text = await fetch("/api/v1/player/account-value/history?format=csv&limit=10").then((response) =>
        response.text()
      );
      downloadText("gw2radar-account-value-history.csv", text, "text/csv");
      return text;
    }),
  refreshOfficialPrices: () =>
    run("dashboard", async () => {
      const refresh = await fetchJson("/api/v1/market/snapshots/official-refresh", { method: "POST" });
      const value = await fetchJson("/api/v1/player/account-value");
      renderAccountValueSummary(value?.data?.account_value_snapshot || {});
      return { refresh, value };
    }),
  apiKeyStatus: () =>
    run("connect", async () => {
      const payload = await fetchJson("/account/api-key/status");
      updateStatusFromKey(payload);
      return payload;
    }),
  apiKeyPermissions: () =>
    run("connect", async () => {
      const payload = await fetchJson("/account/api-key/permissions");
      renderPermissionReport(payload);
      markStep("connect", payload.limited_mode ? "Limited permissions" : "Permissions ready", !payload.limited_mode);
      return payload;
    }),
  connectionDiagnostic: () =>
    run("connect", async () => {
      const payload = await fetchJson("/account/diagnostic");
      updateStatusFromKey(payload.key_status || {});
      renderPermissionReport(payload.permission_report || {});
      updateStatusFromSync(payload.sync_status || {});
      renderConnectionDiagnostic(payload);
      markStep("connect", payload.summary_status === "ready" ? "Connection ready" : "Connection needs review", payload.summary_status === "ready");
      if (payload.summary_status === "ready") {
        markStep("plan", "Account bridge ready");
      }
      return payload;
    }),
  exportDebugBundle: () =>
    run("connect", async () => {
      const payload = await fetchJson("/account/debug-bundle", {
        method: "POST",
        body: JSON.stringify(debugBundleClientState()),
      });
      downloadJson(`gw2radar-account-debug-${new Date().toISOString().replace(/[:.]/g, "-")}.json`, payload);
      renderConnectionDiagnostic({ checks: payload.diagnostic_summary?.checks || [] });
      return payload;
    }),
  deleteApiKey: () =>
    run("privacy", async () => {
      const payload = await fetchJson("/account/api-key", { method: "DELETE" });
      updateStatusFromKey({ has_key: false });
      return payload;
    }),
  deleteSnapshot: () =>
    run("privacy", () => fetchJson("/account/snapshot", { method: "DELETE" })),
  deleteAllPrivateData: () =>
    run("privacy", async () => {
      const payload = await fetchJson("/api/v1/security/private-data", {
        method: "DELETE",
        body: JSON.stringify({
          delete_api_key: true,
          delete_account_snapshot: true,
          delete_private_player_state: true,
          delete_personal_intelligence: true,
          delete_exports: true,
        }),
      });
      updateStatusFromKey({ has_key: false });
      removeStorage(storageKeys.activeBuildId);
      removeStorage(storageKeys.reportHistory);
      return payload;
    }),
  enqueueSync: () =>
    run("connect", async () => {
      const queued = await fetchJson("/api/v1/account/sync", { method: "POST" });
      updateStatusFromSync(queued);
      const drained = await fetchJson("/api/v1/account/sync/drain-one", { method: "POST" });
      updateStatusFromSync(drained);
      const status = await fetchJson("/api/v1/account/sync/status");
      updateStatusFromSync(status);
      let dashboard = null;
      let characterSnapshots = null;
      if (drained.status === "succeeded") {
        dashboard = await fetchJson("/api/v1/player/dashboard");
        renderDashboardPlan(dashboard?.data?.dashboard || {});
        renderFreshnessAnnotations(dashboard?.data?.dashboard?.data_freshness || []);
        const holdings = await fetchJson("/api/v1/player/account-holdings?include_holdings=false");
        renderHoldingSummary(holdings?.data?.account_holding_index || {});
        const value = await fetchJson("/api/v1/player/account-value");
        renderAccountValueSummary(value?.data?.account_value_snapshot || {});
        characterSnapshots = await fetchJson("/api/v1/builds/character-snapshots");
        state.characterSnapshots = characterSnapshots?.data?.snapshots || [];
        renderCharacterSnapshots(state.characterSnapshots);
        markStep("plan", "Account-aware data ready");
        return {
          queued,
          drained,
          status,
          dashboard,
          holdings,
          value,
          character_snapshots: characterSnapshots,
          boundary: "Sync now queues one account snapshot job, drains one local worker job, then refreshes dashboard, holdings, and Build Fit character snapshots when successful.",
        };
      }
      return {
        queued,
        drained,
        status,
        dashboard,
        character_snapshots: characterSnapshots,
        boundary: "Sync now queues one account snapshot job, drains one local worker job, then refreshes dashboard and Build Fit character snapshots when successful.",
      };
    }),
  drainSync: () =>
    run("connect", async () => {
      const payload = await fetchJson("/api/v1/account/sync/drain-one", { method: "POST" });
      updateStatusFromSync(payload);
      if (payload.status === "succeeded") {
        const holdings = await fetchJson("/api/v1/player/account-holdings?include_holdings=false");
        renderHoldingSummary(holdings?.data?.account_holding_index || {});
        const value = await fetchJson("/api/v1/player/account-value");
        renderAccountValueSummary(value?.data?.account_value_snapshot || {});
        const characterSnapshots = await fetchJson("/api/v1/builds/character-snapshots");
        state.characterSnapshots = characterSnapshots?.data?.snapshots || [];
        renderCharacterSnapshots(state.characterSnapshots);
        return { drained: payload, holdings, value, character_snapshots: characterSnapshots };
      }
      return payload;
    }),
  syncStatus: () =>
    run("connect", async () => {
      const payload = await fetchJson("/api/v1/account/sync/status");
      updateStatusFromSync(payload);
      return payload;
    }),
  loadMock: () => run("connect", () => fetchJson("/mock/load", { method: "POST" })),
  loadGoals: () => run("returner", () => fetchJson("/goals")),
  returnerReadiness: () =>
    run("returner", async () => {
      const payload = await fetchJson("/api/v1/returner/readiness?goal_id=gw2:goal:aurora");
      updateReturnerScores(payload?.data?.readiness || {});
      markStep("plan", "Returner readiness scored");
      return payload;
    }),
  returnerReadinessExport: () =>
    run("returner", () => fetch("/api/v1/returner/readiness/export?goal_id=gw2:goal:aurora").then((r) => r.text())),
  returnerFullReport: () =>
    run("returner", () =>
      fetchJson("/api/v1/returner/report", {
        method: "POST",
        body: JSON.stringify({ goal_id: "gw2:goal:aurora", format: "markdown" }),
      }),
    ),
  goalGap: () => run("returner", () => fetchJson("/goals/gw2:goal:aurora/gap")),
  generateActions: () =>
    run("returner", async () => {
      const payload = await fetchJson("/goals/gw2:goal:aurora/actions/generate", { method: "POST" });
      markStep("plan", "7-day action plan ready");
      return payload;
    }),
  kbReport: () => run("returner", () => fetch("/reports/gw2:goal:aurora/markdown/kb").then((r) => r.text())),
  previewReturnerReport: () =>
    run("returner", () =>
      fetchJson("/api/v1/reports/preview", {
        method: "POST",
        body: JSON.stringify({ goal_id: "gw2:goal:aurora", report_type: "returner" }),
      }),
    ),
  addLegendaryGoal: () =>
    run("legendary", () =>
      fetchJson("/api/v1/legendary/goals", {
        method: "POST",
        body: JSON.stringify({
          graph_goal_id: document.querySelector("#legendary-goal").value,
          priority: getNumber("#legendary-priority"),
        }),
      }),
    ),
  legendaryGoalCatalog: () =>
    run("legendary", async () => {
      const payload = await fetchJson("/api/v1/legendary/goals/catalog");
      renderLegendaryGoalCatalog(payload?.data?.goals || []);
      return payload;
    }),
  legendaryPortfolio: () => run("legendary", () => fetchJson("/api/v1/legendary/portfolio")),
  legendaryActions: () => run("legendary", () => fetchJson("/api/v1/legendary/actions")),
  legendaryRecompute: () =>
    run("legendary", async () => {
      const payload = await fetchJson("/api/v1/legendary/recompute", { method: "POST" });
      renderAccountValueEvidenceBridge("#legendary-value-evidence", payload?.data?.planner?.account_value_evidence);
      return payload;
    }),
  legendaryDoNotSell: () => run("legendary", () => fetchJson("/api/v1/legendary/do-not-sell")),
  legendaryReport: () =>
    run("legendary", () =>
      fetchJson("/api/v1/legendary/report", {
        method: "POST",
        body: JSON.stringify({ format: "markdown" }),
      }),
    ),
  marketSnapshot: () =>
    run("legendary", () =>
      fetchJson("/api/v1/market/snapshots", {
        method: "POST",
        body: JSON.stringify({
          item_id: document.querySelector("#market-item-id").value,
          item_name: document.querySelector("#market-item-name").value,
          buy_price_copper: getNumber("#market-buy"),
          sell_price_copper: getNumber("#market-sell"),
          volume: 1000,
          source: "manual_player_ui",
        }),
      }),
    ),
  marketWatch: () =>
    run("legendary", () =>
      fetchJson("/api/v1/market/watchlist", {
        method: "POST",
        body: JSON.stringify({
          item_id: document.querySelector("#market-item-id").value,
          item_name: document.querySelector("#market-item-name").value,
          reason: "Relevant to active legendary goal; observe manually before action.",
        }),
      }),
    ),
  goalCostIndex: () => run("legendary", () => fetchJson("/api/v1/market/goal-cost-index?goal_id=gw2:goal:aurora")),
  marketSignals: () =>
    run("legendary", async () => {
      const payload = await fetchJson("/api/v1/market/signals?goal_id=gw2:goal:aurora");
      renderAccountValueEvidenceBridge("#market-value-evidence", payload?.data?.account_value_evidence);
      return payload;
    }),
  loadAchievementRouteSources: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/sources");
      document.querySelector("#route-source-count").textContent = String(payload?.data?.sources?.length || 0);
      return payload;
    }),
  planAchievementRoute: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/plan", {
        method: "POST",
        body: JSON.stringify(routeRequestPayload()),
      });
      renderRoutePlan(payload?.data?.plan || {});
      markStep("plan", "Route plan ready");
      return payload;
    }),
  exportAchievementRouteMarkdown: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/plan/export?format=markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(routeRequestPayload()),
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  exportAchievementRouteCsv: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/plan/export?format=csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(routeRequestPayload()),
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  fetchOfficialAchievementRoutePreview: () =>
    run("routes", async () => {
      const request = routeOfficialFetchPreviewPayload();
      state.lastRouteFetchRequest = request;
      const payload = await fetchJson("/api/v1/achievement-routes/official-fetch-preview", {
        method: "POST",
        body: JSON.stringify(request),
      });
      renderRouteFetchPreview(payload?.data?.fetch_preview || {});
      return payload;
    }),
  promoteOfficialAchievementRouteReviewed: () =>
    run("routes", async () => {
      const request = state.lastRouteFetchRequest || routeOfficialFetchPreviewPayload();
      state.lastRouteFetchRequest = request;
      const payload = await fetchJson("/api/v1/achievement-routes/official-fetch-preview/promote-reviewed", {
        method: "POST",
        body: JSON.stringify({
          request,
          review: routeReviewPayload(),
        }),
      });
      renderRoutePromotion(payload?.data?.promotion || {});
      await actions.loadAchievementRouteSources();
      return payload;
    }),
  verifyPromotedAchievementRoute: () =>
    run("routes", async () => {
      const sourceId = state.lastRoutePromotionSourceId || document.querySelector("#route-reviewed-source-id").value.trim();
      const payload = await fetchJson("/api/v1/achievement-routes/plan", {
        method: "POST",
        body: JSON.stringify(routeRequestPayload()),
      });
      const plan = payload?.data?.plan || {};
      renderRoutePlan(plan);
      const ingested = sourceId && plan.source_ids?.includes(sourceId);
      document.querySelector("#route-ingested-count").textContent = ingested ? "yes" : "no";
      return payload;
    }),
  loadAchievementRoutePromotionAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}&limit=10` : "?limit=10";
      const payload = await fetchJson(`/api/v1/achievement-routes/promotion-audit${suffix}`);
      renderRoutePromotionAudit(payload?.data?.audit || {});
      return payload;
    }),
  exportAchievementRoutePromotionAudit: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}&format=csv` : "?format=csv";
      return fetch(`/api/v1/achievement-routes/promotion-audit${suffix}`, {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      });
    }),
  loadAchievementRouteReleaseReadiness: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/release-readiness");
      renderRouteReleaseReadiness(payload?.data?.readiness || {});
      return payload;
    }),
  exportAchievementRouteReleaseReadiness: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/release-readiness?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  loadAchievementRouteSourceQuality: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality");
      renderRouteSourceQuality(payload?.data?.quality || {});
      return payload;
    }),
  exportAchievementRouteSourceQuality: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  loadAchievementRouteRemediationQueue: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue");
      renderRouteRemediationQueue(payload?.data?.remediation_queue || {});
      return payload;
    }),
  exportAchievementRouteRemediationQueue: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  reviewAchievementRouteRemediation: () =>
    run("routes", async () => {
      if (!state.lastRouteRemediationItemId) {
        const queuePayload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue");
        renderRouteRemediationQueue(queuePayload?.data?.remediation_queue || {});
      }
      if (!state.lastRouteRemediationItemId) {
        throw new Error("No remediation queue item is available for review.");
      }
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/review", {
        method: "POST",
        body: JSON.stringify({
          item_id: state.lastRouteRemediationItemId,
          status: document.querySelector("#route-remediation-status").value,
          reviewer: document.querySelector("#route-reviewer").value.trim() || "player_ui_operator",
          notes: document.querySelector("#route-review-notes").value.split("\n").map((line) => line.trim()).filter(Boolean),
          evidence_refs: ["/api/v1/achievement-routes/source-quality/remediation-queue"],
          confirmed_manual_review: true,
        }),
      });
      return payload;
    }),
  loadAchievementRouteRemediationReviewAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}&limit=10` : "?limit=10";
      const payload = await fetchJson(`/api/v1/achievement-routes/source-quality/remediation-queue/review-audit${suffix}`);
      renderRouteRemediationReviewAudit(payload?.data?.remediation_review_audit || {});
      return payload;
    }),
  exportAchievementRouteRemediationReviewAudit: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}&format=csv` : "?format=csv";
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/review-audit${suffix}`, {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      });
    }),
  loadAchievementRouteRemediationReadiness: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/readiness");
      renderRouteRemediationReadiness(payload?.data?.remediation_readiness || {});
      return payload;
    }),
  exportAchievementRouteRemediationReadiness: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/readiness?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  loadAchievementRouteOperatorActionBundle: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle", {
        method: "POST",
        body: JSON.stringify({}),
      });
      renderRouteOperatorActionBundle(payload?.data?.operator_action_bundle || {});
      return payload;
    }),
  reviewAchievementRouteRemediationViaBundle: () =>
    run("routes", async () => {
      if (!state.lastRouteRemediationItemId) {
        const queuePayload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue");
        renderRouteRemediationQueue(queuePayload?.data?.remediation_queue || {});
      }
      if (!state.lastRouteRemediationItemId) {
        throw new Error("No remediation queue item is available for bundled review.");
      }
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle", {
        method: "POST",
        body: JSON.stringify({
          review: {
            item_id: state.lastRouteRemediationItemId,
            status: document.querySelector("#route-remediation-status").value,
            reviewer: document.querySelector("#route-reviewer").value.trim() || "player_ui_operator",
            notes: document.querySelector("#route-review-notes").value.split("\n").map((line) => line.trim()).filter(Boolean),
            evidence_refs: ["/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle"],
            confirmed_manual_review: true,
          },
        }),
      });
      renderRouteOperatorActionBundle(payload?.data?.operator_action_bundle || {});
      return payload;
    }),
  loadAchievementRouteOperatorReleasePacket: () =>
    run("routes", () => fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet")),
  exportAchievementRouteOperatorReleasePacket: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  exportAchievementRouteOperatorReleasePacketManifest: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet?format=manifest", {
        headers: { "Accept": "application/json" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return JSON.parse(text);
      }),
    ),
  loadAchievementRouteBackfillCandidates: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates");
      renderRouteBackfillCandidates(payload?.data?.backfill_candidates || {});
      return payload;
    }),
  exportAchievementRouteBackfillCandidates: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  reviewAchievementRouteBackfillCandidate: () =>
    run("routes", async () => {
      if (!state.lastRouteBackfillCandidateId) {
        const candidatesPayload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates");
        renderRouteBackfillCandidates(candidatesPayload?.data?.backfill_candidates || {});
      }
      if (!state.lastRouteBackfillCandidateId) {
        throw new Error("No backfill candidate is available for review.");
      }
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review", {
        method: "POST",
        body: JSON.stringify({
          candidate_id: state.lastRouteBackfillCandidateId,
          status: document.querySelector("#route-remediation-status").value,
          reviewer: document.querySelector("#route-reviewer").value,
          notes: [document.querySelector("#route-review-notes").value],
          evidence_refs: ["/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates"],
          confirmed_manual_review: true,
        }),
      });
      return payload;
    }),
  loadAchievementRouteBackfillCandidateReviewAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}` : "";
      const payload = await fetchJson(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit${suffix}`);
      renderRouteBackfillCandidateReviewAudit(payload?.data?.backfill_candidate_review_audit || {});
      return payload;
    }),
  exportAchievementRouteBackfillCandidateReviewAudit: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `&reviewer=${reviewer}` : "";
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit?format=csv${suffix}`, {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      });
    }),
  loadAchievementRouteBackfillCandidateReadiness: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/readiness");
      renderRouteBackfillCandidateReadiness(payload?.data?.backfill_candidate_readiness || {});
      return payload;
    }),
  exportAchievementRouteBackfillCandidateReadiness: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/readiness?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  loadAchievementRouteSourceEditPatchDraft: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft");
      renderRouteSourceEditPatchDraft(payload?.data?.source_edit_patch_draft || {});
      return payload;
    }),
  exportAchievementRouteSourceEditPatchDraft: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  applyAchievementRouteSourceEditPatchDraft: () =>
    run("routes", async () => {
      if (!state.lastRouteSourcePatchDraftId) {
        const patchPayload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft");
        renderRouteSourceEditPatchDraft(patchPayload?.data?.source_edit_patch_draft || {});
      }
      if (!state.lastRouteSourcePatchDraftId) {
        throw new Error("No source patch draft is available to apply.");
      }
      return fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply", {
        method: "POST",
        body: JSON.stringify({
          draft_id: state.lastRouteSourcePatchDraftId,
          reviewer: document.querySelector("#route-reviewer").value,
          notes: [document.querySelector("#route-review-notes").value],
          evidence_refs: ["/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft"],
          confirmed_manual_review: true,
        }),
      });
    }),
  loadAchievementRouteSourceEditPatchApplyAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}` : "";
      const payload = await fetchJson(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit${suffix}`);
      const latest = payload?.data?.source_edit_patch_apply_audit?.records?.[0];
      if (latest?.output_source_id) {
        state.lastRouteDraftSourceId = latest.output_source_id;
      }
      renderRouteSourceEditPatchApplyAudit(payload?.data?.source_edit_patch_apply_audit || {});
      return payload;
    }),
  exportAchievementRouteSourceEditPatchApplyAudit: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `&reviewer=${reviewer}` : "";
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit?format=csv${suffix}`, {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      });
    }),
  promoteAchievementRouteDraftSource: () =>
    run("routes", async () => {
      if (!state.lastRouteDraftSourceId) {
        const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
        const suffix = reviewer ? `?reviewer=${reviewer}` : "";
        const auditPayload = await fetchJson(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit${suffix}`);
        const latest = auditPayload?.data?.source_edit_patch_apply_audit?.records?.[0];
        if (latest?.output_source_id) {
          state.lastRouteDraftSourceId = latest.output_source_id;
        }
        renderRouteSourceEditPatchApplyAudit(auditPayload?.data?.source_edit_patch_apply_audit || {});
      }
      if (!state.lastRouteDraftSourceId) {
        throw new Error("No draft source manifest is available for promotion.");
      }
      return fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source", {
        method: "POST",
        body: JSON.stringify({
          draft_source_id: state.lastRouteDraftSourceId,
          reviewer: document.querySelector("#route-reviewer").value,
          review_notes: [document.querySelector("#route-review-notes").value],
          evidence_refs: ["/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit"],
          overwrite_existing: true,
          confirmed_reviewed: true,
        }),
      });
    }),
  loadAchievementRouteDraftSourcePromotionAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}` : "";
      const payload = await fetchJson(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit${suffix}`);
      renderRouteDraftSourcePromotionAudit(payload?.data?.draft_source_promotion_audit || {});
      return payload;
    }),
  exportAchievementRouteDraftSourcePromotionAudit: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `&reviewer=${reviewer}` : "";
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit?format=csv${suffix}`, {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      });
    }),
  loadAchievementRouteReleaseEvidenceBundle: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle");
      renderRouteReleaseEvidenceBundle(payload?.data?.release_evidence_bundle || {});
      return payload;
    }),
  exportAchievementRouteReleaseEvidenceBundle: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  exportAchievementRouteReleaseEvidenceBundleManifest: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle?format=manifest", {
        headers: { "Accept": "application/json" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return JSON.parse(text);
      }),
    ),
  archiveAchievementRouteReleaseEvidenceBundle: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim() || "local_operator");
      const payload = await fetchJson(
        `/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?archived_by=${reviewer}&retention_policy=retain_365_days`,
        { method: "POST" },
      );
      renderRouteReleaseEvidenceArchive(payload?.data?.release_evidence_archive || {});
      return payload;
    }),
  loadAchievementRouteReleaseEvidenceArchive: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive");
      renderRouteReleaseEvidenceArchive(payload?.data?.release_evidence_archive_index || {});
      return payload;
    }),
  exportAchievementRouteReleaseEvidenceArchive: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  reviewAchievementRouteReleaseEvidenceArchiveDiff: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff");
      renderRouteReleaseEvidenceArchiveDiff(payload?.data?.release_evidence_archive_diff || {});
      return payload;
    }),
  exportAchievementRouteReleaseEvidenceArchiveDiff: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  signoffAchievementRouteRelease: () =>
    run("routes", async () => {
      const reviewer = document.querySelector("#route-reviewer").value.trim() || "local_operator";
      const notes = document.querySelector("#route-review-notes").value.trim();
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff", {
        method: "POST",
        body: JSON.stringify({
          reviewer,
          notes: notes ? [notes] : ["Player UI release sign-off review."],
          evidence_refs: ["/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff"],
          confirmed_signoff: true,
        }),
      });
      renderRouteReleaseSignoff(payload?.data?.release_signoff || {});
      return payload;
    }),
  loadAchievementRouteReleaseSignoffAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}` : "";
      const payload = await fetchJson(`/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit${suffix}`);
      renderRouteReleaseSignoff(payload?.data?.release_signoff_audit || {});
      return payload;
    }),
  exportAchievementRouteReleaseSignoffAudit: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `&reviewer=${reviewer}` : "";
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit?format=csv${suffix}`, {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      });
    }),
  loadAchievementRouteOperatorReleaseDashboard: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard");
      renderRouteOperatorReleaseDashboard(payload?.data?.operator_release_dashboard || {});
      return payload;
    }),
  exportAchievementRouteOperatorReleaseDashboard: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  loadAchievementRouteReleaseExportPacket: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet");
      renderRouteReleaseExportPacket(payload?.data?.release_export_packet || {});
      return payload;
    }),
  exportAchievementRouteReleaseExportPacket: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet?format=csv", {
        headers: { "Accept": "text/csv" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return text;
      }),
    ),
  exportAchievementRouteReleaseExportPacketManifest: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet?format=manifest", {
        headers: { "Accept": "application/json" },
      }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          throw new Error(text || `HTTP ${response.status}`);
        }
        return JSON.parse(text);
      }),
    ),
  writeAchievementRouteReleaseExportArtifacts: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts", {
        method: "POST",
      });
      renderRouteReleaseExportArtifacts(payload?.data?.release_export_artifacts || {});
      return payload;
    }),
  loadAchievementRouteReleaseExportArtifacts: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts");
      renderRouteReleaseExportArtifacts(payload?.data?.release_export_artifacts || {});
      return payload;
    }),
  openAchievementRouteReleaseExportArtifact: () =>
    run("routes", () => {
      if (!state.lastRouteReleaseExportArtifactPath) {
        throw new Error("No release export artifact path is loaded.");
      }
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/${state.lastRouteReleaseExportArtifactPath}`)
        .then(async (response) => {
          const text = await response.text();
          if (!response.ok) {
            throw new Error(text || `HTTP ${response.status}`);
          }
          return text;
        });
    }),
  loadAchievementRouteReleaseExportBundle: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle?format=manifest");
      renderRouteReleaseExportBundle(payload?.data?.release_export_bundle || {});
      return payload;
    }),
  downloadAchievementRouteReleaseExportBundle: () =>
    run("routes", async () => {
      const response = await fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle");
      const blob = await response.blob();
      if (!response.ok) {
        throw new Error(await blob.text());
      }
      const disposition = response.headers.get("Content-Disposition") || "";
      const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "achievement_route_release_export_bundle.zip";
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      return {
        data: {
          release_export_bundle: {
            file_count: "--",
            size_bytes: blob.size,
          },
        },
      };
    }),
  verifyAchievementRouteReleaseExportBundle: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verify", {
        method: "POST",
      });
      renderRouteReleaseExportBundleVerification(payload?.data?.release_export_bundle_verification || {});
      return payload;
    }),
  recordAchievementRouteReleaseExportBundleVerificationAudit: () =>
    run("routes", async () => {
      const payload = await fetchJson(
        "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit",
        {
          method: "POST",
          body: JSON.stringify({
            reviewer: document.querySelector("#route-reviewer").value.trim() || "player_ui_operator",
            notes: ["Player UI recorded release bundle verification audit."],
          }),
        },
      );
      return payload;
    }),
  loadAchievementRouteReleaseExportBundleVerificationAudit: () =>
    run("routes", async () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}&limit=10` : "?limit=10";
      const payload = await fetchJson(
        `/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit${suffix}`,
      );
      renderRouteReleaseExportBundleVerificationAudit(payload?.data?.release_export_bundle_verification_audit || {});
      return payload;
    }),
  exportAchievementRouteReleaseExportBundleVerificationAuditCsv: () =>
    run("routes", () => {
      const reviewer = encodeURIComponent(document.querySelector("#route-reviewer").value.trim());
      const suffix = reviewer ? `?reviewer=${reviewer}&format=csv` : "?format=csv";
      return fetch(`/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit${suffix}`)
        .then(async (response) => {
          const text = await response.text();
          if (!response.ok) {
            throw new Error(text || `HTTP ${response.status}`);
          }
          return text;
        });
    }),
  loadAchievementRouteOperatorHandoffChecklist: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/handoff-checklist");
      renderRouteOperatorHandoffChecklist(payload?.data?.operator_handoff_checklist || {});
      return payload;
    }),
  exportAchievementRouteOperatorHandoffChecklistCsv: () =>
    run("routes", () =>
      fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/handoff-checklist?format=csv")
        .then(async (response) => {
          const text = await response.text();
          if (!response.ok) {
            throw new Error(text || `HTTP ${response.status}`);
          }
          return text;
        }),
    ),
  loadAchievementRouteReleaseNotes: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/release-notes");
      renderRouteFinalReleaseArtifact("#route-release-notes-count", payload?.data?.release_notes || {});
      return payload;
    }),
  exportAchievementRouteReleaseNotesCsv: () =>
    run("routes", () => fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/release-notes?format=csv").then((response) => response.text())),
  loadAchievementRouteOperatorRunbook: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/operator-runbook");
      renderRouteFinalReleaseArtifact("#route-operator-runbook-count", payload?.data?.operator_runbook || {});
      return payload;
    }),
  exportAchievementRouteOperatorRunbookCsv: () =>
    run("routes", () => fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/operator-runbook?format=csv").then((response) => response.text())),
  loadAchievementRouteFinalReleaseDashboard: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/final-dashboard");
      renderRouteFinalReleaseArtifact("#route-final-release-dashboard-count", payload?.data?.final_release_dashboard || {});
      return payload;
    }),
  exportAchievementRouteFinalReleaseDashboardCsv: () =>
    run("routes", () => fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/final-dashboard?format=csv").then((response) => response.text())),
  loadAchievementRouteFinalMaturityAudit: () =>
    run("routes", async () => {
      const payload = await fetchJson("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/final-maturity-audit");
      renderRouteFinalReleaseArtifact("#route-final-maturity-audit-count", payload?.data?.final_maturity_audit || {});
      return payload;
    }),
  exportAchievementRouteFinalMaturityAuditCsv: () =>
    run("routes", () => fetch("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/final-maturity-audit?format=csv").then((response) => response.text())),
  importBuild: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/builds/import", {
        method: "POST",
        body: JSON.stringify(buildImportPayload()),
      });
      const buildId = payload?.data?.build?.build_id;
      if (buildId) {
        state.activeBuildId = buildId;
        document.querySelector("#active-build-id").value = buildId;
        localStorage.setItem(storageKeys.activeBuildId, buildId);
        markStep("plan", "Build imported");
      }
      return payload;
    }),
  loadCharacterSnapshots: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/builds/character-snapshots");
      state.characterSnapshots = payload?.data?.snapshots || [];
      renderCharacterSnapshots(state.characterSnapshots);
      return payload;
    }),
  applyCharacterSnapshot: () =>
    run("build", async () => {
      const snapshotId = document.querySelector("#character-snapshot").value;
      if (!snapshotId) {
        state.selectedAccountGear = null;
        document.querySelector("#gear-summary").textContent = "Manual lightweight snapshot: chest only.";
        return { status: "manual_mode", boundary: "Manual fields only; no sample character snapshot selected." };
      }
      const payload = await fetchJson(`/api/v1/builds/character-snapshots/${encodeURIComponent(snapshotId)}/account-gear`);
      applyAccountGearSnapshot(payload.data.snapshot, payload.data.account_gear);
      return payload;
    }),
  listBuilds: () => run("build", () => fetchJson("/api/v1/builds")),
  evaluateBuild: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/builds/fit", {
        method: "POST",
        body: JSON.stringify({ build_id: requireActiveBuildId(), account_gear: accountGearPayload() }),
      });
      renderAccountValueEvidenceBridge("#build-value-evidence", payload?.data?.fit?.transition_plan?.account_value_evidence);
      return payload;
    }),
  transitionPlan: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/builds/transition-plan", {
        method: "POST",
        body: JSON.stringify({ build_id: requireActiveBuildId(), account_gear: accountGearPayload() }),
      });
      renderAccountValueEvidenceBridge("#build-value-evidence", payload?.data?.transition_plan?.account_value_evidence);
      return payload;
    }),
  buildFreshness: () => run("build", () => fetchJson(`/api/v1/builds/${encodeURIComponent(requireActiveBuildId())}/patch-freshness`)),
  previewBuildUpgradeRules: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/kb/rule-packs/build_upgrade_effects");
      renderBuildUpgradeRules(payload?.data?.pack?.rules || []);
      return payload;
    }),
  importBuildUpgradeRules: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/kb/rule-packs/build_upgrade_effects/import", {
        method: "POST",
        body: JSON.stringify({ confirmed: true }),
      });
      const rules = payload?.data?.result?.rules || [];
      renderBuildUpgradeRules(rules);
      return payload;
    }),
  listBuildUpgradeRules: () =>
    run("build", async () => {
      const payload = await fetchJson("/api/v1/kb/rules?domain=build&name_contains=Build%20upgrade");
      renderBuildUpgradeRules(payload?.data?.rules || []);
      return payload;
    }),
  enableBuildUpgradeRule: () =>
    run("build", async () => {
      let ruleId = document.querySelector("#build-upgrade-rule-id").value;
      if (!ruleId) {
        const rule = state.buildUpgradeRules.find((item) => item.rule_id && !item.enabled);
        ruleId = rule?.rule_id || "";
      }
      if (!ruleId) {
        throw new Error("Import or list disabled upgrade rules before enabling one.");
      }
      const payload = await fetchJson(`/api/v1/kb/rules/${encodeURIComponent(ruleId)}/enable`, {
        method: "POST",
        body: JSON.stringify({
          confirmed_reviewed: true,
          reviewer: document.querySelector("#build-rule-reviewer").value || "player_ui_reviewer",
        }),
      });
      await actions.listBuildUpgradeRules();
      return payload;
    }),
  buildReport: () =>
    run("build", () =>
      fetchJson("/api/v1/builds/report", {
        method: "POST",
        body: JSON.stringify({ build_id: requireActiveBuildId(), account_gear: accountGearPayload(), format: "markdown" }),
      }),
    ),
  reportProducts: () => run("reports", () => fetchJson("/api/v1/reports/products")),
  pricingPlans: () => run("reports", () => fetchJson("/api/v1/growth/pricing")),
  checkoutLegendary: () =>
    run("reports", async () => {
      const payload = await fetchJson("/api/v1/growth/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_id: "plan_legendary_once", user_id: "local-user" }),
      });
      state.lastCheckoutId = payload?.data?.checkout?.checkout_session_id || "";
      if (!state.lastCheckoutId) {
        return payload;
      }
      const completed = await fetchJson(`/api/v1/growth/checkout/${state.lastCheckoutId}/complete`, { method: "POST" });
      return { checkout: payload, completed };
    }),
  checkoutReturner: () =>
    run("reports", async () => {
      const payload = await fetchJson("/api/v1/growth/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_id: "plan_returner_once", user_id: "local-user" }),
      });
      state.lastCheckoutId = payload?.data?.checkout?.checkout_session_id || "";
      if (!state.lastCheckoutId) {
        return payload;
      }
      const completed = await fetchJson(`/api/v1/growth/checkout/${state.lastCheckoutId}/complete`, { method: "POST" });
      return { checkout: payload, completed };
    }),
  reportJob: () => {
    const jobId = document.querySelector("#report-job-id").value;
    return run("reports", () => fetchJson(`/api/v1/reports/jobs/${encodeURIComponent(jobId)}`));
  },
  showReportHistory: () =>
    run("reports", async () => ({
      report_history: reportHistory(),
      note: "Stored locally in this browser for convenience only.",
    })),
  clearReportHistory: () =>
    run("reports", async () => {
      removeStorage(storageKeys.reportHistory);
      return { status: "cleared", report_history: [] };
    }),
  refreshFreshness: () =>
    run("freshness", async () => {
      const sync = await fetchJson("/api/v1/account/sync/status");
      const market = await fetchJson("/api/v1/market/patch-freshness");
      const annotations = await fetchJson("/api/v1/player/freshness-annotations");
      updateStatusFromSync(sync);
      renderFreshnessAnnotations(annotations?.data?.annotations || []);
      return {
        account_snapshot: sync,
        market_patch_freshness: market,
        freshness_annotations: annotations,
        build_sources: "Check per imported build.",
        knowledge_rules: "Reviewed enabled rules only.",
        boundary: "Planning guidance only; refresh stale data before manual action.",
      };
    }),
  openArtifact: () => {
    const artifactId = document.querySelector("#artifact-id").value;
    if (artifactId) {
      window.open(`/api/v1/reports/artifacts/${encodeURIComponent(artifactId)}`, "_blank", "noopener");
    }
  },
};

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

document.querySelectorAll("[data-view-link]").forEach((card) => {
  card.addEventListener("click", () => {
    if (card.dataset.intent) {
      actions.selectIntent(card.dataset.intent);
    }
    showView(card.dataset.viewLink);
  });
});

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    const action = actions[button.dataset.action];
    if (action) {
      action();
    }
  });
});

document.querySelector('[data-form="apiKey"]').addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.querySelector("#api-key-input");
  run("connect", async () => {
    const payload = await fetchJson("/account/api-key", {
      method: "PUT",
      body: JSON.stringify({ api_key: input.value }),
    });
    input.value = "";
    updateStatusFromKey(payload);
    return payload;
  });
});

function restoreLocalState() {
  const savedIntent = readStorage(storageKeys.playerIntent);
  if (savedIntent) {
    state.playerIntent = savedIntent;
    renderSummary("welcome", `Restored intent: ${savedIntent}.`);
  }
  const savedBuildId = readStorage(storageKeys.activeBuildId);
  if (savedBuildId) {
    state.activeBuildId = savedBuildId;
    document.querySelector("#active-build-id").value = savedBuildId;
    markStep("plan", "Previous build restored");
  }
  const savedView = readStorage(storageKeys.activeView);
  if (savedView && document.querySelector(`#${savedView}`)) {
    showView(savedView);
  }
}

restoreLocalState();
actions.refreshDashboard();
