from enum import StrEnum

from pydantic import BaseModel, Field


class MaturityLevel(StrEnum):
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    LOW = "low"


class SemanticAxis(StrEnum):
    STATE = "state"
    ENTITY = "entity"
    CONSTRAINT = "constraint"


class SemanticGraphNode(BaseModel):
    node_id: str
    label: str
    node_type: str
    maturity: MaturityLevel
    anchors: list[str] = Field(default_factory=list)


class SemanticGraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class SemanticAxisEntry(BaseModel):
    axis: SemanticAxis
    name: str
    maturity: MaturityLevel
    anchors: list[str] = Field(default_factory=list)
    notes: str


class MaturityComponent(BaseModel):
    component_id: str
    name: str
    maturity: MaturityLevel
    score: float = Field(ge=0.0, le=1.0)
    implemented: list[str] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    next_priority: str | None = None


class PriorityRecommendation(BaseModel):
    priority_id: str
    title: str
    rationale: str
    acceptance: list[str] = Field(default_factory=list)


class KbSemanticMaturityReport(BaseModel):
    schema_version: str
    overall_score: float
    maturity_label: str
    graph_nodes: list[SemanticGraphNode]
    graph_edges: list[SemanticGraphEdge]
    axes: list[SemanticAxisEntry]
    components: list[MaturityComponent]
    recommended_priorities: list[PriorityRecommendation]


def build_kb_semantic_maturity_report() -> KbSemanticMaturityReport:
    components = _components()
    overall_score = round(sum(component.score for component in components) / len(components), 3)
    return KbSemanticMaturityReport(
        schema_version="gw2radar.kb_semantic_maturity.v1",
        overall_score=overall_score,
        maturity_label=_maturity_label(overall_score),
        graph_nodes=_graph_nodes(),
        graph_edges=_graph_edges(),
        axes=_axes(),
        components=components,
        recommended_priorities=_priorities(),
    )


def render_kb_semantic_maturity_markdown(report: KbSemanticMaturityReport) -> str:
    lines = [
        "# KB Semantic Maturity Analysis",
        "",
        f"- schema_version: `{report.schema_version}`",
        f"- overall_score: `{report.overall_score:.3f}`",
        f"- maturity_label: `{report.maturity_label}`",
        "",
        "## Semantic Graph",
        "",
        "| Node | Type | Maturity | Anchors |",
        "|---|---|---|---|",
    ]
    for node in report.graph_nodes:
        lines.append(
            f"| {node.label} | {node.node_type} | {node.maturity.value} | {_join(node.anchors)} |"
        )
    lines.extend(["", "## Triple-Axis Extraction", "", "| Axis | Name | Maturity | Notes |", "|---|---|---|---|"])
    for entry in report.axes:
        lines.append(f"| {entry.axis.value} | {entry.name} | {entry.maturity.value} | {entry.notes} |")
    lines.extend(
        [
            "",
            "## Component Maturity",
            "",
            "| Component | Score | Maturity | Implemented | Remaining Gaps |",
            "|---|---:|---|---|---|",
        ]
    )
    for component in report.components:
        lines.append(
            f"| {component.name} | {component.score:.2f} | {component.maturity.value} | {_join(component.implemented)} | {_join(component.remaining_gaps)} |"
        )
    lines.extend(["", "## Recommended Priorities", ""])
    for priority in report.recommended_priorities:
        lines.extend(
            [
                f"### {priority.priority_id} {priority.title}",
                "",
                f"- Rationale: {priority.rationale}",
                f"- Acceptance: {_join(priority.acceptance)}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _graph_nodes() -> list[SemanticGraphNode]:
    return [
        SemanticGraphNode(
            node_id="source_registry",
            label="Source Registry",
            node_type="evidence_source",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_models.SourceRegistry", "kb_repository.register_source"],
        ),
        SemanticGraphNode(
            node_id="kb_article",
            label="Knowledge Article",
            node_type="knowledge_entity",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_models.KnowledgeArticle", "kb_markdown_loader.load_markdown_directory"],
        ),
        SemanticGraphNode(
            node_id="entity_linker",
            label="Entity Linker",
            node_type="semantic_validation",
            maturity=MaturityLevel.MEDIUM_HIGH,
            anchors=["kb_entity_linker.validate_article_links"],
        ),
        SemanticGraphNode(
            node_id="knowledge_rule",
            label="Knowledge Rule",
            node_type="reviewed_rule",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_models.KnowledgeRule", "kb_repository.enable_rule"],
        ),
        SemanticGraphNode(
            node_id="domain_rule_pack",
            label="Domain Rule Pack",
            node_type="reviewed_rule_pack",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_domain_rule_packs", "kb routes /rule-packs"],
        ),
        SemanticGraphNode(
            node_id="promotion_planner",
            label="KB Promotion Planner",
            node_type="batch_validation_workflow",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_promotion_planner", "kb routes /promotion-plan"],
        ),
        SemanticGraphNode(
            node_id="source_semantics",
            label="Official Source Semantics",
            node_type="source_semantic_extraction",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_source_semantics", "kb routes /source-semantics"],
        ),
        SemanticGraphNode(
            node_id="patch_freshness",
            label="Patch Freshness Integration",
            node_type="commercial_review_notice",
            maturity=MaturityLevel.HIGH,
            anchors=["commercial.patch_freshness", "builds /patch-freshness", "market /patch-freshness"],
        ),
        SemanticGraphNode(
            node_id="release_readiness",
            label="KB Release Readiness",
            node_type="operator_gate",
            maturity=MaturityLevel.HIGH,
            anchors=["kb_release_readiness", "kb routes /release-readiness"],
        ),
        SemanticGraphNode(
            node_id="patch_review",
            label="Patch Review Workflow",
            node_type="review_workflow",
            maturity=MaturityLevel.HIGH,
            anchors=["patch_impact_review", "patch_rule_audit", "patch_dashboard_export"],
        ),
        SemanticGraphNode(
            node_id="report_artifact",
            label="KB-backed Report Artifact",
            node_type="commercial_output",
            maturity=MaturityLevel.HIGH,
            anchors=["commercial.report_engine", "reports.markdown_report"],
        ),
    ]


def _graph_edges() -> list[SemanticGraphEdge]:
    return [
        SemanticGraphEdge(source="source_registry", target="kb_article", relation="authorizes_source_refs"),
        SemanticGraphEdge(source="kb_article", target="entity_linker", relation="validates_links"),
        SemanticGraphEdge(source="promotion_planner", target="entity_linker", relation="batch_validates_article_links"),
        SemanticGraphEdge(source="source_semantics", target="entity_linker", relation="extracts_ontology_hints"),
        SemanticGraphEdge(source="kb_article", target="knowledge_rule", relation="distills_reviewed_rule"),
        SemanticGraphEdge(source="promotion_planner", target="knowledge_rule", relation="previews_distillable_rules"),
        SemanticGraphEdge(source="domain_rule_pack", target="knowledge_rule", relation="imports_reviewed_disabled_rules"),
        SemanticGraphEdge(source="promotion_planner", target="domain_rule_pack", relation="previews_rule_pack_imports"),
        SemanticGraphEdge(source="knowledge_rule", target="report_artifact", relation="explains_recommendation"),
        SemanticGraphEdge(source="patch_review", target="knowledge_rule", relation="promotes_patch_candidate"),
        SemanticGraphEdge(source="source_semantics", target="patch_review", relation="adds_patch_source_hints"),
        SemanticGraphEdge(source="patch_review", target="patch_freshness", relation="creates_manual_review_notices"),
        SemanticGraphEdge(source="source_semantics", target="patch_freshness", relation="adds_source_hint_notices"),
        SemanticGraphEdge(source="patch_freshness", target="report_artifact", relation="adds_build_market_review_section"),
        SemanticGraphEdge(source="patch_review", target="report_artifact", relation="adds_patch_audit_provenance"),
        SemanticGraphEdge(source="source_semantics", target="release_readiness", relation="feeds_operator_gate"),
        SemanticGraphEdge(source="promotion_planner", target="release_readiness", relation="feeds_operator_gate"),
        SemanticGraphEdge(source="patch_review", target="release_readiness", relation="feeds_operator_gate"),
        SemanticGraphEdge(source="domain_rule_pack", target="release_readiness", relation="feeds_operator_gate"),
    ]


def _axes() -> list[SemanticAxisEntry]:
    return [
        SemanticAxisEntry(
            axis=SemanticAxis.STATE,
            name="Review and publication states",
            maturity=MaturityLevel.HIGH,
            anchors=["KnowledgeReviewStatus", "PatchReviewDashboardItem.lifecycle_status", "KbPromotionPlan"],
            notes="draft/reviewed/needs_update/deprecated plus patch lifecycle and promotion readiness are explicit and tested.",
        ),
        SemanticAxisEntry(
            axis=SemanticAxis.ENTITY,
            name="KB and patch entities",
            maturity=MaturityLevel.HIGH,
            anchors=["SourceRegistry", "KnowledgeArticle", "KnowledgeRule", "PatchRuleAuditEvent"],
            notes="Core KB entities and patch-derived rule provenance are modeled with Pydantic and persistence.",
        ),
        SemanticAxisEntry(
            axis=SemanticAxis.CONSTRAINT,
            name="Review gates and safety boundaries",
            maturity=MaturityLevel.HIGH,
            anchors=["KnowledgeRuleInput.validate_rule_contract", "persist_patch_rule_candidates", "enable_rule"],
            notes="Unreviewed rules cannot be enabled or drive high-priority actions; patch rule persistence and enablement require confirmation.",
        ),
        SemanticAxisEntry(
            axis=SemanticAxis.ENTITY,
            name="Domain KB coverage",
            maturity=MaturityLevel.MEDIUM_HIGH,
            anchors=["docs/knowledge_base", "kb_domain_rule_packs"],
            notes="Official and patch KB are strong; returner/build/market now have reviewed disabled rule packs, while guild/creator depth remains thinner.",
        ),
    ]


def _components() -> list[MaturityComponent]:
    return [
        MaturityComponent(
            component_id="kb_schema_repository",
            name="KB schema and repository",
            maturity=MaturityLevel.HIGH,
            score=0.95,
            implemented=["SourceRegistry", "KnowledgeArticle", "KnowledgeChunk", "KnowledgeRule", "review/deprecate APIs"],
            remaining_gaps=["bulk operational tooling"],
        ),
        MaturityComponent(
            component_id="kb_linker_distiller",
            name="Entity linker and rule distiller",
            maturity=MaturityLevel.HIGH,
            score=0.91,
            implemented=[
                "link validation",
                "reviewed article to KnowledgeRule",
                "action schema guard",
                "batch promotion planner",
                "Markdown/CSV promotion exports",
            ],
            remaining_gaps=["richer ontology relation validation"],
            next_priority="P14 official source semantic extraction",
        ),
        MaturityComponent(
            component_id="kb_explanation_reports",
            name="KB-backed explanations and paid artifacts",
            maturity=MaturityLevel.HIGH,
            score=0.9,
            implemented=["reviewed enabled rules only", "report quality manifest", "patch audit manifest"],
            remaining_gaps=["domain-specific rule coverage depth"],
        ),
        MaturityComponent(
            component_id="official_pdf_sources",
            name="Official PDF source processing",
            maturity=MaturityLevel.HIGH,
            score=0.92,
            implemented=[
                "inventory",
                "evidence",
                "API docs",
                "patch summaries",
                "official news summaries",
                "summary-only semantic hint extraction",
                "source semantics Markdown/CSV exports",
            ],
            remaining_gaps=["entity-specific extraction beyond structured stubs"],
            next_priority="P15 patch impact to build/market freshness integration",
        ),
        MaturityComponent(
            component_id="patch_review_operations",
            name="Patch review operations",
            maturity=MaturityLevel.HIGH,
            score=0.95,
            implemented=[
                "review queue",
                "rule candidates",
                "confirmation gate",
                "audit trail",
                "dashboard",
                "admin workflow bundle",
                "build freshness notices",
                "market watchlist freshness notices",
                "report freshness sections",
            ],
            remaining_gaps=["deeper entity-level patch matching"],
            next_priority="P16 guild/creator policy rule packs",
        ),
        MaturityComponent(
            component_id="domain_rule_packs",
            name="Domain KB rule packs",
            maturity=MaturityLevel.HIGH,
            score=0.92,
            implemented=[
                "seed domains",
                "core explanation infrastructure",
                "reviewed disabled returner/build/market rule packs",
                "reviewed disabled guild/creator policy rule packs",
                "confirmation-gated rule pack import API",
                "rule pack promotion preview",
            ],
            remaining_gaps=["admin UI workflow"],
            next_priority="P18 admin release console workflow",
        ),
        MaturityComponent(
            component_id="kb_release_readiness",
            name="KB release readiness and operating playbook",
            maturity=MaturityLevel.HIGH,
            score=0.9,
            implemented=[
                "release readiness gate",
                "operator checklist",
                "rule pack import/enable playbook",
                "source semantics readiness",
                "promotion blockers readiness",
                "patch dashboard/audit readiness",
                "Markdown/CSV release exports",
            ],
            remaining_gaps=["front-end admin console"],
            next_priority="P18 admin release console workflow",
        ),
    ]


def _priorities() -> list[PriorityRecommendation]:
    return [
        PriorityRecommendation(
            priority_id="P18",
            title="Admin Release Console Workflow",
            rationale="The KB operating loop now has a release readiness API; a front-end friendly admin workflow can combine checklist, exports, import, enable, and audit queries.",
            acceptance=[
                "front-end friendly release readiness bundle",
                "link checklist items to existing admin actions",
                "surface export payloads",
                "preserve confirmation gates for import and enable",
            ],
        ),
    ]


def _maturity_label(score: float) -> str:
    if score >= 0.85:
        return "mature_mvp_semantic_spine"
    if score >= 0.7:
        return "usable_with_domain_depth_gaps"
    return "immature"


def _join(values: list[str]) -> str:
    return "; ".join(values) if values else "none"
