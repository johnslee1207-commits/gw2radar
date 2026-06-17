const state = {
  activeBuildId: "",
  lastCheckoutId: "",
};

const outputs = {
  dashboard: document.querySelector("#dashboard-output"),
  connect: document.querySelector("#connect-output"),
  returner: document.querySelector("#returner-output"),
  legendary: document.querySelector("#legendary-output"),
  build: document.querySelector("#build-output"),
  reports: document.querySelector("#reports-output"),
  privacy: document.querySelector("#privacy-output"),
};

function showView(viewId) {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active-view", view.id === viewId);
  });
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewId);
  });
}

function render(target, value) {
  const element = outputs[target] || outputs.dashboard;
  element.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
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
  try {
    const result = await work();
    render(target, result);
    return result;
  } catch (error) {
    render(target, `Request failed:\n${error.message}`);
    return null;
  }
}

function updateStatusFromKey(payload) {
  const status = document.querySelector("#account-status");
  const hasKey = payload?.has_key || payload?.data?.has_key || payload?.status === "stored";
  status.textContent = hasKey ? "Account key stored" : "No API key stored";
  status.className = `status-pill ${hasKey ? "good" : "warn"}`;
  document.querySelector("#metric-connection").textContent = hasKey ? "Connected" : "Not connected";
}

function updateStatusFromSync(payload) {
  const status = document.querySelector("#sync-status");
  const label = payload?.status || payload?.queue_status || "Sync status updated";
  status.textContent = String(label);
  status.className = "status-pill good";
  document.querySelector("#metric-sync").textContent = new Date().toLocaleString();
}

function getNumber(selector) {
  return Number(document.querySelector(selector).value || 0);
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

function activeBuildId() {
  return document.querySelector("#active-build-id").value || state.activeBuildId;
}

const actions = {
  refreshDashboard: () =>
    run("dashboard", async () => {
      const key = await fetchJson("/account/api-key/status");
      updateStatusFromKey(key);
      const sync = await fetchJson("/api/v1/account/sync/status");
      updateStatusFromSync(sync);
      return { account: key, sync };
    }),
  apiKeyStatus: () =>
    run("connect", async () => {
      const payload = await fetchJson("/account/api-key/status");
      updateStatusFromKey(payload);
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
  enqueueSync: () =>
    run("connect", async () => {
      const payload = await fetchJson("/api/v1/account/sync", { method: "POST" });
      updateStatusFromSync(payload);
      return payload;
    }),
  drainSync: () =>
    run("connect", async () => {
      const payload = await fetchJson("/api/v1/account/sync/drain-one", { method: "POST" });
      updateStatusFromSync(payload);
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
  goalGap: () => run("returner", () => fetchJson("/goals/gw2:goal:aurora/gap")),
  generateActions: () =>
    run("returner", () => fetchJson("/goals/gw2:goal:aurora/actions/generate", { method: "POST" })),
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
  legendaryPortfolio: () => run("legendary", () => fetchJson("/api/v1/legendary/portfolio")),
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
      }
      return payload;
    }),
  listBuilds: () => run("build", () => fetchJson("/api/v1/builds")),
  evaluateBuild: () =>
    run("build", () =>
      fetchJson("/api/v1/builds/fit", {
        method: "POST",
        body: JSON.stringify({ build_id: activeBuildId(), account_gear: accountGearPayload() }),
      }),
    ),
  transitionPlan: () =>
    run("build", () =>
      fetchJson("/api/v1/builds/transition-plan", {
        method: "POST",
        body: JSON.stringify({ build_id: activeBuildId(), account_gear: accountGearPayload() }),
      }),
    ),
  buildFreshness: () => run("build", () => fetchJson(`/api/v1/builds/${encodeURIComponent(activeBuildId())}/patch-freshness`)),
  buildReport: () =>
    run("build", () =>
      fetchJson("/api/v1/builds/report", {
        method: "POST",
        body: JSON.stringify({ build_id: activeBuildId(), account_gear: accountGearPayload(), format: "markdown" }),
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
  reportJob: () => {
    const jobId = document.querySelector("#report-job-id").value;
    return run("reports", () => fetchJson(`/api/v1/reports/jobs/${encodeURIComponent(jobId)}`));
  },
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
  card.addEventListener("click", () => showView(card.dataset.viewLink));
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
    updateStatusFromKey({ has_key: true });
    return payload;
  });
});

actions.refreshDashboard();
