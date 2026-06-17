from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb.kb_entity_linker import validate_article_links
from gw2radar.kb.kb_explanation import explain_actions_with_kb
from gw2radar.kb.kb_domain_rule_packs import (
    DomainRulePackId,
    get_domain_rule_pack,
    import_domain_rule_pack,
    list_domain_rule_packs,
)
from gw2radar.kb.kb_markdown_loader import load_markdown_directory
from gw2radar.kb.kb_models import KnowledgeArticleInput, KnowledgeDomain, SourceRegistryInput, SourceType
from gw2radar.kb.kb_promotion_planner import (
    build_kb_promotion_plan,
    render_kb_promotion_plan_csv,
    render_kb_promotion_plan_markdown,
)
from gw2radar.kb.kb_report_quality import score_kb_report_quality
from gw2radar.kb.kb_repository import (
    create_article,
    deprecate_article,
    enable_rule,
    get_article,
    get_source,
    list_articles,
    list_sources,
    list_rules,
    register_source,
    review_article,
    search_articles,
)
from gw2radar.kb.kb_rule_distiller import distill_rule_from_article
from gw2radar.kb.kb_semantic_maturity import (
    build_kb_semantic_maturity_report,
    render_kb_semantic_maturity_markdown,
)
from gw2radar.kb.kb_source_semantics import (
    build_source_semantic_report,
    render_source_semantic_report_csv,
    render_source_semantic_report_markdown,
)
from gw2radar.kb.patch_dashboard_export import render_patch_dashboard_csv, render_patch_dashboard_markdown
from gw2radar.kb.patch_impact_review import (
    PatchImpactReviewInput,
    build_patch_review_dashboard,
    build_patch_rule_candidates,
    list_patch_impact_drafts,
    list_pending_patch_impact_drafts,
    persist_patch_rule_candidates,
    save_patch_impact_review,
)
from gw2radar.kb.patch_rule_audit import (
    PatchRuleAuditAction,
    list_patch_rule_audit_events,
    record_patch_rule_audit_event,
)
from gw2radar.inference.action_generator import generate_actions

router = APIRouter(prefix="/api/v1/kb", tags=["kb"])


class LoadDirectoryRequest(BaseModel):
    directory: str = "docs/knowledge_base"


class ConfirmPatchRulePersistenceRequest(BaseModel):
    confirmed: bool = False


class EnableKnowledgeRuleRequest(BaseModel):
    confirmed_reviewed: bool = False
    reviewer: str = "manual_reviewer"


class ImportDomainRulePackRequest(BaseModel):
    confirmed: bool = False


class PatchReviewAdminWorkflowRequest(BaseModel):
    year: int | None = None
    patch_id: str | None = None
    review: PatchImpactReviewInput | None = None
    persist_confirmed: bool = False
    enable_rule_ids: list[str] = []
    enable_confirmed: bool = False
    reviewer: str = "manual_reviewer"
    include_markdown_export: bool = False
    include_csv_export: bool = False


@router.post("/sources", response_model=ApiDataEnvelope)
def post_kb_source(request: SourceRegistryInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        source = register_source(session, request)
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.get("/sources", response_model=ApiDataEnvelope)
def get_kb_sources(source_type: SourceType | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        sources = [
            source.model_dump(mode="json")
            for source in list_sources(session, source_type.value if source_type else None)
        ]
    return ApiDataEnvelope(data={"sources": sources})


@router.get("/sources/{source_id}", response_model=ApiDataEnvelope)
def get_kb_source(source_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        source = get_source(session, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.post("/load-directory", response_model=ApiDataEnvelope)
def post_kb_load_directory(request: LoadDirectoryRequest) -> ApiDataEnvelope:
    init_db()
    directory = Path(request.directory)
    with db_session.SessionLocal() as session:
        try:
            articles = [article.model_dump(mode="json") for article in load_markdown_directory(session, directory)]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"loaded_count": len(articles), "articles": articles})


@router.post("/articles", response_model=ApiDataEnvelope)
def post_kb_article(request: KnowledgeArticleInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            article = create_article(session, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.get("/articles", response_model=ApiDataEnvelope)
def get_kb_articles(domain: KnowledgeDomain | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        articles = [article.model_dump(mode="json") for article in list_articles(session, domain)]
    return ApiDataEnvelope(data={"articles": articles})


@router.get("/articles/{kb_id}", response_model=ApiDataEnvelope)
def get_kb_article(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        article = get_article(session, kb_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found.")
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.post("/articles/{kb_id}/review", response_model=ApiDataEnvelope)
def post_kb_article_review(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            article = review_article(session, kb_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.post("/articles/{kb_id}/deprecate", response_model=ApiDataEnvelope)
def post_kb_article_deprecate(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            article = deprecate_article(session, kb_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.post("/articles/{kb_id}/validate-links", response_model=ApiDataEnvelope)
def post_kb_article_validate_links(kb_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        article = get_article(session, kb_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found.")
    result = validate_article_links(article, graph)
    return ApiDataEnvelope(data={"validation": result.model_dump(mode="json")})


@router.post("/articles/{kb_id}/distill-rule", response_model=ApiDataEnvelope)
def post_kb_article_distill_rule(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        article = get_article(session, kb_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Knowledge article not found.")
        try:
            rule = distill_rule_from_article(session, article)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"rule": rule.model_dump(mode="json")})


@router.get("/search", response_model=ApiDataEnvelope)
def get_kb_search(q: str, domain: KnowledgeDomain | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        articles = [article.model_dump(mode="json") for article in search_articles(session, q, domain)]
    return ApiDataEnvelope(data={"articles": articles})


@router.get("/semantic-maturity", response_model=ApiDataEnvelope)
def get_kb_semantic_maturity() -> ApiDataEnvelope:
    report = build_kb_semantic_maturity_report()
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.get("/semantic-maturity/export")
def get_kb_semantic_maturity_export(format: str = "markdown") -> Response:
    report = build_kb_semantic_maturity_report()
    if format == "markdown":
        return Response(
            content=render_kb_semantic_maturity_markdown(report),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported semantic maturity export format.")


@router.get("/promotion-plan", response_model=ApiDataEnvelope)
def get_kb_promotion_plan(
    domain: KnowledgeDomain | None = None,
    include_rule_packs: bool = True,
) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        articles = list_articles(session, domain)
    plan = build_kb_promotion_plan(
        articles,
        graph,
        domain=domain,
        include_rule_packs=include_rule_packs,
    )
    return ApiDataEnvelope(data={"plan": plan.model_dump(mode="json")})


@router.get("/promotion-plan/export")
def get_kb_promotion_plan_export(
    domain: KnowledgeDomain | None = None,
    include_rule_packs: bool = True,
    format: str = "markdown",
) -> Response:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        articles = list_articles(session, domain)
    plan = build_kb_promotion_plan(
        articles,
        graph,
        domain=domain,
        include_rule_packs=include_rule_packs,
    )
    if format == "markdown":
        return Response(
            content=render_kb_promotion_plan_markdown(plan),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_kb_promotion_plan_csv(plan),
            media_type="text/csv; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported promotion plan export format.")


@router.get("/source-semantics", response_model=ApiDataEnvelope)
def get_kb_source_semantics(
    source_root: str = "docs/knowledge_base",
    limit: int | None = None,
) -> ApiDataEnvelope:
    try:
        report = build_source_semantic_report(Path(source_root), limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.get("/source-semantics/export")
def get_kb_source_semantics_export(
    source_root: str = "docs/knowledge_base",
    limit: int | None = None,
    format: str = "markdown",
) -> Response:
    try:
        report = build_source_semantic_report(Path(source_root), limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if format == "markdown":
        return Response(
            content=render_source_semantic_report_markdown(report),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_source_semantic_report_csv(report),
            media_type="text/csv; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported source semantics export format.")


@router.get("/rule-packs", response_model=ApiDataEnvelope)
def get_kb_rule_packs() -> ApiDataEnvelope:
    packs = list_domain_rule_packs()
    return ApiDataEnvelope(
        data={
            "count": len(packs),
            "packs": [pack.model_dump(mode="json") for pack in packs],
        }
    )


@router.get("/rule-packs/{pack_id}", response_model=ApiDataEnvelope)
def get_kb_rule_pack(pack_id: DomainRulePackId) -> ApiDataEnvelope:
    pack = get_domain_rule_pack(pack_id)
    return ApiDataEnvelope(data={"pack": pack.model_dump(mode="json")})


@router.post("/rule-packs/{pack_id}/import", response_model=ApiDataEnvelope)
def post_kb_rule_pack_import(
    pack_id: DomainRulePackId,
    request: ImportDomainRulePackRequest,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            result = import_domain_rule_pack(session, pack_id, confirmed=request.confirmed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"result": result.model_dump(mode="json")})


@router.get("/patch-impact/drafts", response_model=ApiDataEnvelope)
def get_patch_impact_drafts(year: int | None = None, pending_only: bool = False) -> ApiDataEnvelope:
    drafts = (
        list_pending_patch_impact_drafts(year=year)
        if pending_only
        else list_patch_impact_drafts(year=year)
    )
    return ApiDataEnvelope(
        data={
            "count": len(drafts),
            "drafts": [draft.model_dump(mode="json") for draft in drafts],
        }
    )


@router.get("/patch-impact/dashboard", response_model=ApiDataEnvelope)
def get_patch_impact_dashboard(year: int | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    items = build_patch_review_dashboard(rules, year=year)
    lifecycle_counts: dict[str, int] = {}
    for item in items:
        lifecycle_counts[item.lifecycle_status] = lifecycle_counts.get(item.lifecycle_status, 0) + 1
    return ApiDataEnvelope(
        data={
            "count": len(items),
            "lifecycle_counts": lifecycle_counts,
            "items": [item.model_dump(mode="json") for item in items],
        }
    )


@router.get("/patch-impact/dashboard/export")
def get_patch_impact_dashboard_export(year: int | None = None, format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    items = build_patch_review_dashboard(rules, year=year)
    if format == "markdown":
        return Response(
            content=render_patch_dashboard_markdown(items),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_patch_dashboard_csv(items),
            media_type="text/csv; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported dashboard export format.")


@router.post("/patch-impact/admin/workflow", response_model=ApiDataEnvelope)
def post_patch_impact_admin_workflow(request: PatchReviewAdminWorkflowRequest) -> ApiDataEnvelope:
    action_results: dict[str, object] = {}
    patch_id = request.patch_id or (request.review.patch_id if request.review else None)

    if request.review is not None:
        try:
            review = save_patch_impact_review(request.review)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        patch_id = review.patch_id
        action_results["review"] = review.model_dump(mode="json")

    init_db()
    with db_session.SessionLocal() as session:
        if request.persist_confirmed:
            if patch_id is None:
                raise HTTPException(status_code=400, detail="patch_id is required to persist patch rule candidates.")
            try:
                persisted = persist_patch_rule_candidates(session, patch_id, confirmed=True)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            action_results["persist"] = {
                "created_count": persisted.created_count,
                "skipped_existing_count": persisted.skipped_existing_count,
                "rules": [rule.model_dump(mode="json") for rule in persisted.rules],
            }

        enabled_rules = []
        if request.enable_rule_ids:
            if not request.enable_confirmed:
                raise HTTPException(status_code=400, detail="Enabling KnowledgeRule records requires confirmation.")
            for rule_id in request.enable_rule_ids:
                try:
                    rule = enable_rule(session, rule_id)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
                rule_patch_id = _patch_id_from_rule(rule.condition)
                if rule_patch_id is not None:
                    patch_id = patch_id or rule_patch_id
                    record_patch_rule_audit_event(
                        PatchRuleAuditAction.ENABLE,
                        patch_id=rule_patch_id,
                        rule_id=rule.rule_id,
                        reviewer=request.reviewer,
                        evidence_refs=rule.evidence_refs,
                        details={"enabled": rule.enabled, "action_type": rule.action_type},
                    )
                enabled_rules.append(rule.model_dump(mode="json"))
            action_results["enable"] = {"rules": enabled_rules}

        rules = list_rules(session)

    dashboard_items = build_patch_review_dashboard(rules, year=request.year)
    lifecycle_counts: dict[str, int] = {}
    for item in dashboard_items:
        lifecycle_counts[item.lifecycle_status] = lifecycle_counts.get(item.lifecycle_status, 0) + 1
    audit_events = list_patch_rule_audit_events(patch_id=patch_id) if patch_id else list_patch_rule_audit_events()
    exports: dict[str, str] = {}
    if request.include_markdown_export:
        exports["markdown"] = render_patch_dashboard_markdown(dashboard_items)
    if request.include_csv_export:
        exports["csv"] = render_patch_dashboard_csv(dashboard_items)

    return ApiDataEnvelope(
        data={
            "patch_id": patch_id,
            "actions": action_results,
            "dashboard": {
                "count": len(dashboard_items),
                "lifecycle_counts": lifecycle_counts,
                "items": [item.model_dump(mode="json") for item in dashboard_items],
            },
            "audit": {
                "count": len(audit_events),
                "events": [event.model_dump(mode="json") for event in audit_events],
            },
            "exports": exports,
        }
    )


@router.post("/patch-impact/reviews", response_model=ApiDataEnvelope)
def post_patch_impact_review(request: PatchImpactReviewInput) -> ApiDataEnvelope:
    try:
        review = save_patch_impact_review(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"review": review.model_dump(mode="json")})


@router.get("/patch-impact/{patch_id}/rule-candidates", response_model=ApiDataEnvelope)
def get_patch_impact_rule_candidates(patch_id: str) -> ApiDataEnvelope:
    try:
        candidate = build_patch_rule_candidates(patch_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={
            "patch_id": candidate.patch_id,
            "rules": [rule.model_dump(mode="json") for rule in candidate.rules],
        }
    )


@router.post("/patch-impact/{patch_id}/rule-candidates/persist", response_model=ApiDataEnvelope)
def post_patch_impact_rule_candidates_persist(
    patch_id: str,
    request: ConfirmPatchRulePersistenceRequest,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            result = persist_patch_rule_candidates(session, patch_id, confirmed=request.confirmed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={
            "patch_id": result.patch_id,
            "created_count": result.created_count,
            "skipped_existing_count": result.skipped_existing_count,
            "rules": [rule.model_dump(mode="json") for rule in result.rules],
        }
    )


@router.post("/rules/{rule_id}/enable", response_model=ApiDataEnvelope)
def post_kb_rule_enable(rule_id: str, request: EnableKnowledgeRuleRequest) -> ApiDataEnvelope:
    if not request.confirmed_reviewed:
        raise HTTPException(status_code=400, detail="Enabling a KnowledgeRule requires reviewed confirmation.")
    init_db()
    with db_session.SessionLocal() as session:
        try:
            rule = enable_rule(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    patch_id = _patch_id_from_rule(rule.condition)
    if patch_id is not None:
        record_patch_rule_audit_event(
            PatchRuleAuditAction.ENABLE,
            patch_id=patch_id,
            rule_id=rule.rule_id,
            reviewer=request.reviewer,
            evidence_refs=rule.evidence_refs,
            details={"enabled": rule.enabled, "action_type": rule.action_type},
        )
    return ApiDataEnvelope(data={"rule": rule.model_dump(mode="json")})


@router.get("/patch-impact/audit", response_model=ApiDataEnvelope)
def get_patch_impact_audit(patch_id: str | None = None, rule_id: str | None = None) -> ApiDataEnvelope:
    events = list_patch_rule_audit_events(patch_id=patch_id, rule_id=rule_id)
    return ApiDataEnvelope(
        data={
            "count": len(events),
            "events": [event.model_dump(mode="json") for event in events],
        }
    )


@router.get("/goals/{goal_id}/action-explanations", response_model=ApiDataEnvelope)
def get_kb_action_explanations(goal_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    explanations = explain_actions_with_kb(actions, rules)
    return ApiDataEnvelope(
        data={
            "goal_id": goal_id,
            "explanations": {
                action_id: [item.model_dump(mode="json") for item in items]
                for action_id, items in explanations.items()
            },
        }
    )


@router.get("/goals/{goal_id}/report-quality", response_model=ApiDataEnvelope)
def get_kb_report_quality(goal_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    explanations = explain_actions_with_kb(actions, rules)
    quality = score_kb_report_quality(actions, rules, explanations)
    return ApiDataEnvelope(data={"goal_id": goal_id, "quality": quality.model_dump(mode="json")})


def _patch_id_from_rule(condition: str) -> str | None:
    if not condition.startswith("patch_review:"):
        return None
    parts = condition.split(":")
    if len(parts) < 3:
        return None
    return f"{parts[1]}:{parts[2]}"
