from __future__ import annotations

from uuid import uuid4

from gw2radar.player_os.intent.models import PlanAction, PlayerIntent, PlayerPlan, WorkflowState


SAFETY_BOUNDARIES = [
    "Plans are advisory and require manual player action.",
    "No gameplay automation is performed.",
    "No automated trading or guaranteed profit claims are generated.",
    "Private account data is summarized only and must not enter public KB content.",
]


def build_workflow_and_plan(intent: PlayerIntent) -> tuple[WorkflowState, PlayerPlan]:
    if intent.intent_type == "returner":
        return _returner(intent)
    if intent.intent_type == "legendary":
        return _legendary(intent)
    if intent.intent_type == "build_fit":
        return _build_fit(intent)
    if intent.intent_type in {"what_should_i_do_now", "account_overview", "market_watch"}:
        return _now(intent)
    return _clarify(intent)


def _workflow(intent: PlayerIntent, workflow_type: str, status: str, current_step: str, actions: list[str]) -> WorkflowState:
    return WorkflowState(
        workflow_id=f"workflow-{uuid4().hex[:12]}",
        intent_id=intent.intent_id,
        workflow_type=workflow_type,
        status=status,
        current_step=current_step,
        required_user_actions=actions,
        warnings=list(intent.warnings),
        evidence_refs=[
            "/account/first-run-summary",
            "/account/diagnostic",
            "/api/v1/player/readiness",
        ],
    )


def _plan(
    intent: PlayerIntent,
    workflow: WorkflowState,
    *,
    title: str,
    focus: str,
    top_actions: list[PlanAction],
    this_week: list[PlanAction],
    warnings: list[str] | None = None,
) -> PlayerPlan:
    return PlayerPlan(
        plan_id=f"plan-{uuid4().hex[:12]}",
        intent_id=intent.intent_id,
        workflow_id=workflow.workflow_id,
        intent_type=intent.intent_type,
        title=title,
        focus=focus,
        top_actions=top_actions,
        this_week=this_week,
        assumptions=[
            "Planner uses current GW2Radar local data and reviewed rules only.",
            "Missing or stale facts are shown as warnings instead of being invented.",
        ],
        warnings=[*(warnings or []), *intent.warnings],
        evidence_refs=workflow.evidence_refs,
        constraints=dict(intent.constraints),
        safety_boundaries=SAFETY_BOUNDARIES,
        freshness_notes=[
            "Refresh account sync before treating account-aware actions as current.",
            "Market context is informational and does not trigger trades.",
        ],
    )


def _returner(intent: PlayerIntent) -> tuple[WorkflowState, PlayerPlan]:
    workflow = _workflow(
        intent,
        "returner_wizard",
        "checking_account",
        "check_account",
        ["Check API key status.", "Run account sync if first-run summary is not ready."],
    )
    goal = intent.goal_id or intent.constraints.get("goal_id") or "gw2:goal:aurora"
    profession = intent.profession or intent.constraints.get("preferred_profession") or "your safest level-80 character"
    plan = _plan(
        intent,
        workflow,
        title="Returner Recovery Plan",
        focus=f"Restart safely with {profession} while protecting progress toward {goal}.",
        top_actions=[
            PlanAction(title="Run connection diagnostic", reason="Confirms key, permissions, sync, private layer, and Build Fit bridge.", urgency="high", confidence=0.95, evidence_refs=["/account/diagnostic"]),
            PlanAction(title="Open Account Readiness", reason="Finds stale systems and blocked account-aware workflows before choosing a goal.", confidence=0.85, evidence_refs=["/api/v1/player/readiness"]),
            PlanAction(title="Protect do-not-sell materials", reason="Avoids selling materials that may be needed for active legendary goals.", linked_goal=goal, confidence=0.85, evidence_refs=["/api/v1/legendary/do-not-sell"]),
        ],
        this_week=[
            PlanAction(title="Day 1: recover account state", reason="Sync, inspect readiness, and pick the safest character.", confidence=0.9),
            PlanAction(title="Day 2-3: rebuild routine", reason="Use short open-world actions before committing to expensive upgrades.", confidence=0.75, risk_reason="Generic advice; verify against actual account state."),
            PlanAction(title="Day 4-7: resume goal progress", reason="Start only the reviewed Aurora-safe actions that match your constraints.", linked_goal=goal, confidence=0.7, risk_reason="Depends on account sync completeness; review readiness first."),
        ],
    )
    return workflow, plan


def _legendary(intent: PlayerIntent) -> tuple[WorkflowState, PlayerPlan]:
    workflow = _workflow(
        intent,
        "legendary_wizard",
        "planning",
        "analyze_gap",
        ["Confirm the legendary goal.", "Refresh account holdings before acting on missing requirements."],
    )
    goal = intent.goal_id or intent.constraints.get("goal_id") or "gw2:goal:aurora"
    avoid = ", ".join(intent.constraints.get("avoid_modes", [])) or "none"
    plan = _plan(
        intent,
        workflow,
        title="Legendary Goal Plan",
        focus=f"Plan {goal} with spending mode {intent.constraints.get('spending_mode', 'balanced')} and avoided modes: {avoid}.",
        top_actions=[
            PlanAction(title="Recompute legendary portfolio", reason="Builds shared requirements, missing items, and do-not-sell guidance.", urgency="high", linked_goal=goal, confidence=0.9, evidence_refs=["/api/v1/legendary/recompute"]),
            PlanAction(title="Review do-not-sell", reason="Protects materials that should not be liquidated for short-term gold.", linked_goal=goal, confidence=0.85, evidence_refs=["/api/v1/legendary/do-not-sell"]),
            PlanAction(title="Choose cheap/fast path", reason="Applies budget and play-mode constraints to the action plan.", linked_goal=goal, confidence=0.8, risk_reason="Path selection depends on current market prices; review before committing.", execution_risk="price_volatility_risk", liquidity_reason="Cost estimates use latest snapshots; verify prices before large purchases.", evidence_refs=["/api/v1/legendary/actions"]),
        ],
        this_week=[
            PlanAction(title="Finish low-risk daily progress", reason="Prefer repeatable, reviewed tasks over speculative purchases.", linked_goal=goal, confidence=0.9),
            PlanAction(title="Defer unsupported route constraints", reason="If WvW avoidance cannot be verified, mark it as an assumption.", linked_goal=goal, confidence=0.7, risk_reason="Constraint verification depends on KB rule coverage and player state."),
        ],
    )
    return workflow, plan


def _build_fit(intent: PlayerIntent) -> tuple[WorkflowState, PlayerPlan]:
    workflow = _workflow(
        intent,
        "build_fit_wizard",
        "needs_user_choice",
        "select_build",
        ["Select or import a reviewed build.", "Load a synced character snapshot."],
    )
    target = " ".join(item for item in [intent.game_mode, intent.specialization or intent.profession] if item) or "selected build"
    budget = intent.constraints.get("budget_gold_limit")
    budget_text = f" within {budget}g" if budget is not None else ""
    plan = _plan(
        intent,
        workflow,
        title="Build Fit Plan",
        focus=f"Check whether your account can play {target}{budget_text}.",
        top_actions=[
            PlanAction(title="Load synced character snapshot", reason="Build Fit needs character gear before it can score account fit.", urgency="high", confidence=0.95, evidence_refs=["/api/v1/builds/character-snapshots"]),
            PlanAction(title="Run fit score", reason="Compares reviewed build requirements against available account gear.", confidence=0.85, evidence_refs=["/api/v1/builds/fit"]),
            PlanAction(title="Review transition plan", reason="Shows reusable gear, missing upgrades, cost estimate, and budget alternative.", confidence=0.8, risk_reason="Cost estimates depend on current market snapshots.", execution_risk="material_cost_risk", liquidity_reason="Verify TP prices before committing to upgrade purchases.", evidence_refs=["/api/v1/builds/transition-plan"]),
        ],
        this_week=[
            PlanAction(title="Use budget alternative first", reason="Avoids over-spending until the selected build and patch freshness are reviewed.", confidence=0.75, risk_reason="Patch freshness affects build viability; verify before committing.", execution_risk="material_cost_risk", liquidity_reason="Budget alternatives may use different TP-listed materials; compare prices."),
        ],
        warnings=["Unreviewed build sources cannot drive strong recommendations."],
    )
    return workflow, plan


def _now(intent: PlayerIntent) -> tuple[WorkflowState, PlayerPlan]:
    workflow = _workflow(
        intent,
        "what_should_i_do_now_wizard",
        "ready",
        "generate_top_actions",
        ["Refresh status if account-aware panels look empty."],
    )
    time_limit = intent.constraints.get("daily_time_limit", "30m")
    plan = _plan(
        intent,
        workflow,
        title="What Should I Do Now?",
        focus=f"Pick the highest-signal manual actions for the next {time_limit}.",
        top_actions=[
            PlanAction(title="Refresh first-run summary", reason="Shows whether account-aware outputs are ready or blocked.", urgency="high", confidence=0.95, evidence_refs=["/account/first-run-summary"]),
            PlanAction(title="Do one protected goal action", reason="Keeps progress aligned with do-not-sell and account readiness.", linked_goal=intent.goal_id or intent.constraints.get("goal_id"), confidence=0.8, risk_reason="Goal protection depends on active reservations being up-to-date.", execution_risk="timing_risk", liquidity_reason="Check do-not-sell and market prices before buying or selling materials."),
            PlanAction(title="Save a support-safe snapshot if output is still empty", reason="Creates metadata-only evidence for trial defect triage.", confidence=0.9, evidence_refs=["/account/debug-bundle"]),
        ],
        this_week=[
            PlanAction(title="Review readiness history", reason="Compare sync and price-refresh changes before changing strategy.", confidence=0.85),
            PlanAction(title="Generate one report preview", reason="Use a deterministic report to preserve assumptions and evidence.", confidence=0.9),
        ],
    )
    return workflow, plan


def _clarify(intent: PlayerIntent) -> tuple[WorkflowState, PlayerPlan]:
    workflow = _workflow(
        intent,
        "clarification",
        "needs_user_choice",
        "clarify_intent",
        ["Choose returner, legendary, build, market, or what should I do now."],
    )
    plan = _plan(
        intent,
        workflow,
        title="Clarify Player Goal",
        focus="The request needs one more choice before a strong plan can be generated.",
        top_actions=[
            PlanAction(title="Choose a template", reason="Templates keep the plan deterministic and evidence-backed.", urgency="high", confidence=0.6, risk_reason="Intent is unclear; template selection may not match your actual goal.", evidence_refs=["/api/v1/templates"]),
        ],
        this_week=[],
        warnings=["Low-confidence intent cannot produce a strong recommendation."],
    )
    return workflow, plan
