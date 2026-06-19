const state = {
  activeBuildId: "",
  lastCheckoutId: "",
  playerIntent: "",
  characterSnapshots: [],
  selectedAccountGear: null,
  buildUpgradeRules: [],
  lastRouteFetchRequest: null,
  lastRoutePromotionSourceId: "",
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
    "/v2/account/achievements": "sync-achievements",
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
  document.querySelector("#freshness-account-card").textContent = `Account sync state checked: ${label}`;
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
      return { account: key, sync, dashboard };
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
        characterSnapshots = await fetchJson("/api/v1/builds/character-snapshots");
        state.characterSnapshots = characterSnapshots?.data?.snapshots || [];
        renderCharacterSnapshots(state.characterSnapshots);
        markStep("plan", "Account-aware data ready");
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
        const characterSnapshots = await fetchJson("/api/v1/builds/character-snapshots");
        state.characterSnapshots = characterSnapshots?.data?.snapshots || [];
        renderCharacterSnapshots(state.characterSnapshots);
        return { drained: payload, character_snapshots: characterSnapshots };
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
  legendaryRecompute: () => run("legendary", () => fetchJson("/api/v1/legendary/recompute", { method: "POST" })),
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
  marketSignals: () => run("legendary", () => fetchJson("/api/v1/market/signals?goal_id=gw2:goal:aurora")),
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
    run("build", () =>
      fetchJson("/api/v1/builds/fit", {
        method: "POST",
        body: JSON.stringify({ build_id: requireActiveBuildId(), account_gear: accountGearPayload() }),
      }),
    ),
  transitionPlan: () =>
    run("build", () =>
      fetchJson("/api/v1/builds/transition-plan", {
        method: "POST",
        body: JSON.stringify({ build_id: requireActiveBuildId(), account_gear: accountGearPayload() }),
      }),
    ),
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
