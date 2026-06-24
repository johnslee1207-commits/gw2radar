from __future__ import annotations

from pydantic import BaseModel


class AegisReferenceSignal(BaseModel):
    signal_id: str
    aegis_anchor: str
    pattern: str
    gw2radar_mapping: str
    adoption_decision: str


class BorrowingPriority(BaseModel):
    priority_id: str
    title: str
    reason: str
    deliverables: list[str]
    acceptance_checks: list[str]
    maturity_impact: str


class AegisBorrowingAssessment(BaseModel):
    schema_version: str = "gw2radar.aegisradar_borrowing_assessment.v1"
    status: str
    reference_repo: str
    reference_repo_state: str
    summary: str
    process_flow_signals: list[AegisReferenceSignal]
    ontology_signals: list[AegisReferenceSignal]
    ux_signals: list[AegisReferenceSignal]
    adopt_now: list[BorrowingPriority]
    defer: list[BorrowingPriority]
    explicit_non_goals: list[str]
    next_priority: str


def build_aegisradar_borrowing_assessment() -> AegisBorrowingAssessment:
    return AegisBorrowingAssessment(
        status="ready_for_targeted_adaptation",
        reference_repo="D:\\Projects\\AegisRadar",
        reference_repo_state=(
            "Read-only reference. The AegisRadar worktree has local changes, so GW2Radar must not "
            "copy files or depend on that repo at runtime."
        ),
        summary=(
            "AegisRadar is most useful as a lifecycle and ontology operating model: domain-pack "
            "driven ingestion, separated fact/graph/ontology layers, audit-backed rule promotion, "
            "credential readiness, and a front-door UX organized around connect, choose, receive. "
            "GW2Radar should borrow those structures while keeping the GW2 player domain, privacy "
            "boundaries, and current trial stop-line."
        ),
        process_flow_signals=[
            AegisReferenceSignal(
                signal_id="domain_pack_pipeline",
                aegis_anchor="D:\\Projects\\AegisRadar\\README.md",
                pattern="Domain Pack YAML drives extraction, scoring, audit rules, graph build, and exports.",
                gw2radar_mapping=(
                    "Use reviewed GW2 KB/source packs and route source manifests as the equivalent "
                    "configuration surface for planners, reports, and patch impact rules."
                ),
                adoption_decision="adopt_as_pack_lifecycle",
            ),
            AegisReferenceSignal(
                signal_id="shared_pipeline_steps",
                aegis_anchor="D:\\Projects\\AegisRadar\\apps\\api\\app\\jobs\\run_pipeline.py",
                pattern="A regular pipeline records reusable steps and can run offline demo paths.",
                gw2radar_mapping=(
                    "Consolidate repeated GW2 review, promotion, export, archive, and sign-off flows "
                    "behind shared lifecycle helpers instead of adding another bespoke phase chain."
                ),
                adoption_decision="adopt_as_refactor_direction",
            ),
            AegisReferenceSignal(
                signal_id="control_plane_boundaries",
                aegis_anchor="D:\\Projects\\AegisRadar\\docs\\admin_console.md",
                pattern="Admin is an intelligence OS control plane with operable and read-only classes.",
                gw2radar_mapping=(
                    "Keep GW2 operator views separate from player views: support triage and release "
                    "gates are operator surfaces, while account guidance remains player-facing."
                ),
                adoption_decision="adopt_as_ux_boundary",
            ),
        ],
        ontology_signals=[
            AegisReferenceSignal(
                signal_id="three_layer_graph",
                aegis_anchor="D:\\Projects\\AegisRadar\\docs\\graph_ontology.md",
                pattern="Evidence facts, intelligence graph, and ontology graph are separate layers.",
                gw2radar_mapping=(
                    "GW2Radar already separates public_game, private_player_state, and "
                    "personal_intelligence. The missing Aegis-style depth is explicit ontology "
                    "validation and conflict surfacing for promoted rule packs."
                ),
                adoption_decision="adopt_validation_depth",
            ),
            AegisReferenceSignal(
                signal_id="ontology_conflict_audit",
                aegis_anchor="D:\\Projects\\AegisRadar\\core\\graph\\validator.py",
                pattern="Invalid ontology relations and missing evidence become audit tasks.",
                gw2radar_mapping=(
                    "Route invalid GW2 rule links, unsupported patch claims, and private/public "
                    "layer mismatches into review queues instead of silently excluding them."
                ),
                adoption_decision="adopt_for_kb_and_patch_rules",
            ),
            AegisReferenceSignal(
                signal_id="rule_dry_run_toggle",
                aegis_anchor="D:\\Projects\\AegisRadar\\apps\\api\\app\\routes\\graph.py",
                pattern="Ontology rules can be dry-run, compared, viewed in history, and toggled.",
                gw2radar_mapping=(
                    "Extend existing reviewed KnowledgeRule enable gates with dry-run impact counts "
                    "before enabling rules that affect player recommendations."
                ),
                adoption_decision="adopt_after_trial_defects",
            ),
        ],
        ux_signals=[
            AegisReferenceSignal(
                signal_id="three_step_user_journey",
                aegis_anchor="D:\\Projects\\AegisRadar\\docs\\user_journey_guide.md",
                pattern="User journey is connect data sources, choose product, receive deliverable.",
                gw2radar_mapping=(
                    "Translate to GW2 player language: connect API key, choose intent "
                    "(legendary, build, market, returner), receive next actions and report."
                ),
                adoption_decision="adopt_for_player_cockpit_information_architecture",
            ),
            AegisReferenceSignal(
                signal_id="credential_readiness_cards",
                aegis_anchor="D:\\Projects\\AegisRadar\\core\\credentials\\readiness.py",
                pattern="Report readiness explains missing providers and disabled outputs.",
                gw2radar_mapping=(
                    "Use account permission readiness and sync health as visible prerequisites for "
                    "account value, Build Fit, Legendary Planner, and Market Radar outputs."
                ),
                adoption_decision="adopt_for_real_api_key_feedback",
            ),
            AegisReferenceSignal(
                signal_id="lineage_and_deliverables",
                aegis_anchor="D:\\Projects\\AegisRadar\\apps\\web\\pages\\deliverables",
                pattern="Deliverables and lineage are separate destinations in the user journey.",
                gw2radar_mapping=(
                    "Keep GW2 reports downloadable, but expose evidence lineage inline so senior "
                    "players can verify why a recommendation was made."
                ),
                adoption_decision="adopt_as_report_center_polish",
            ),
        ],
        adopt_now=[
            BorrowingPriority(
                priority_id="p0_trial_key_flow_visibility",
                title="Aegis-style credential readiness for real GW2 API key flow",
                reason=(
                    "Recent user feedback says valid keys can connect without visible outputs. "
                    "Aegis solves similar confusion with readiness cards and provider requirements."
                ),
                deliverables=[
                    "Player-facing prerequisite status for key saved, scopes, sync job, snapshots, and selected workflow.",
                    "No-output empty states that name the missing lifecycle step.",
                    "Support bundle evidence names aligned with the trial defect triage classifications.",
                ],
                acceptance_checks=[
                    "Real-key flow never asks for or displays raw API keys.",
                    "Every blocked account-aware panel shows a visible next action.",
                    "Diagnostic metadata can classify empty output without private payloads.",
                ],
                maturity_impact="Raises UX and support maturity from trial-ready to trial-observable.",
            ),
            BorrowingPriority(
                priority_id="p1_shared_lifecycle_primitives",
                title="Replace repeated review/persist/enable/export phase chains with lifecycle primitives",
                reason=(
                    "The current efficiency bottleneck is repeated horizontal implementation of the "
                    "same operating lifecycle. Aegis uses shared pipeline and control-plane patterns."
                ),
                deliverables=[
                    "Shared status model for draft, reviewed, persisted, enabled, exported, archived, signed_off.",
                    "Common audit event renderer for KB, patch, route source, and release evidence objects.",
                    "One harness that validates lifecycle transitions for at least two existing domains.",
                ],
                acceptance_checks=[
                    "No behavior regression in existing KB patch and achievement route gates.",
                    "New lifecycle helper is covered by unit tests and one smoke harness.",
                    "Generated artifacts remain deterministic and metadata-only.",
                ],
                maturity_impact="Improves delivery speed and reduces duplicate phase code.",
            ),
            BorrowingPriority(
                priority_id="p2_ontology_validation_queue",
                title="Aegis-style ontology conflict and missing evidence queue for GW2 rules",
                reason=(
                    "GW2Radar has strong schemas and layers, but Aegis has a clearer pattern for "
                    "turning invalid semantic edges into reviewable work."
                ),
                deliverables=[
                    "Rule candidate validation against entity/action/relation schemas before promotion.",
                    "Conflict findings for unsupported relation, missing evidence, private/public mismatch, and stale patch source.",
                    "Markdown/CSV queue export for operator review.",
                ],
                acceptance_checks=[
                    "Invalid rule candidates default to disabled and cannot affect recommendations.",
                    "Findings cite source ids and evidence refs, not raw private payloads.",
                    "Validated rules expose dry-run impact counts before enable.",
                ],
                maturity_impact="Raises KB-backed recommendation maturity from reviewed-rule MVP to auditable ontology operations.",
            ),
        ],
        defer=[
            BorrowingPriority(
                priority_id="d1_full_domain_pack_admin",
                title="Full Aegis-style domain pack CMS/admin",
                reason="GW2Radar is in player-trial closeout; a full admin CMS would expand scope.",
                deliverables=["Post-trial operator workbench only if real reviewer throughput requires it."],
                acceptance_checks=["Must not replace current simple reviewed source files during trial."],
                maturity_impact="Useful later for content operations, not needed for immediate player validation.",
            ),
            BorrowingPriority(
                priority_id="d2_pgvector_graph_rag_stack",
                title="Postgres pgvector GraphRAG parity",
                reason="Aegis uses deeper data platform pieces, but GW2Radar can validate product value locally first.",
                deliverables=["Production data layer design after trial evidence confirms demand."],
                acceptance_checks=["No dependency on external vector services for MVP player flows."],
                maturity_impact="Production scalability improvement, not a current blocker.",
            ),
        ],
        explicit_non_goals=[
            "Do not copy AegisRadar CO2 or market-entry business logic into GW2Radar.",
            "Do not add automated trading, guaranteed profit claims, or gameplay automation.",
            "Do not make GW2Radar depend on D:\\Projects\\AegisRadar at runtime.",
            "Do not expose private account payloads, raw API keys, or unreviewed rule content in public artifacts.",
        ],
        next_priority=(
            "Implement p0_trial_key_flow_visibility first, then refactor repeated lifecycle code only where "
            "it directly shortens current KB, route, and release gate maintenance."
        ),
    )


def render_aegisradar_borrowing_markdown(assessment: AegisBorrowingAssessment) -> str:
    lines = [
        "# AegisRadar Borrowing Assessment",
        "",
        f"- Schema: {assessment.schema_version}",
        f"- Status: {assessment.status}",
        f"- Reference repo: `{assessment.reference_repo}`",
        f"- Reference repo state: {assessment.reference_repo_state}",
        "",
        "## Summary",
        "",
        assessment.summary,
        "",
        "## Reference Signals",
        "",
    ]
    for title, signals in (
        ("Process Flow", assessment.process_flow_signals),
        ("Ontology", assessment.ontology_signals),
        ("Final-User UX", assessment.ux_signals),
    ):
        lines.extend([f"### {title}", ""])
        lines.extend(
            [
                "| Signal | Aegis Anchor | Pattern | GW2Radar Mapping | Decision |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for signal in signals:
            lines.append(
                "| "
                + " | ".join(
                    [
                        signal.signal_id,
                        f"`{signal.aegis_anchor}`",
                        signal.pattern,
                        signal.gw2radar_mapping,
                        signal.adoption_decision,
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(["## Adopt Now", ""])
    for priority in assessment.adopt_now:
        lines.extend(_priority_lines(priority))

    lines.extend(["## Defer", ""])
    for priority in assessment.defer:
        lines.extend(_priority_lines(priority))

    lines.extend(["## Explicit Non-Goals", ""])
    for item in assessment.explicit_non_goals:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Priority", "", assessment.next_priority, ""])
    return "\n".join(lines)


def _priority_lines(priority: BorrowingPriority) -> list[str]:
    lines = [
        f"### {priority.priority_id}: {priority.title}",
        "",
        f"Reason: {priority.reason}",
        "",
        "Deliverables:",
    ]
    lines.extend(f"- {item}" for item in priority.deliverables)
    lines.extend(["", "Acceptance checks:"])
    lines.extend(f"- {item}" for item in priority.acceptance_checks)
    lines.extend(["", f"Maturity impact: {priority.maturity_impact}", ""])
    return lines
