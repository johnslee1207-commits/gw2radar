from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.commercial.market_radar import validate_market_language
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRule, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule, list_rules
from gw2radar.ontology.action_types import ActionType


class DomainRulePackId(StrEnum):
    RETURNER_RECOVERY = "returner_recovery"
    BUILD_FIT_FRESHNESS = "build_fit_freshness"
    MARKET_RETENTION = "market_retention"


class DomainRulePack(BaseModel):
    pack_id: DomainRulePackId
    title: str
    domain: KnowledgeDomain
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    rules: list[KnowledgeRuleInput]


class DomainRulePackImportResult(BaseModel):
    pack_id: DomainRulePackId
    created_count: int
    skipped_existing_count: int
    rules: list[KnowledgeRule]


def list_domain_rule_packs() -> list[DomainRulePack]:
    return [_build_pack(pack_id) for pack_id in DomainRulePackId]


def get_domain_rule_pack(pack_id: DomainRulePackId | str) -> DomainRulePack:
    return _build_pack(DomainRulePackId(pack_id))


def import_domain_rule_pack(
    session: Session,
    pack_id: DomainRulePackId | str,
    *,
    confirmed: bool,
) -> DomainRulePackImportResult:
    if not confirmed:
        raise ValueError("Importing reviewed domain rule packs requires confirmation.")
    pack = get_domain_rule_pack(pack_id)
    existing_keys = {
        _rule_key(rule.name, rule.domain, rule.condition)
        for rule in list_rules(session, pack.domain)
    }
    created: list[KnowledgeRule] = []
    skipped = 0
    for candidate in pack.rules:
        if candidate.enabled:
            raise ValueError("Domain rule pack candidates must remain disabled until enable review.")
        key = _rule_key(candidate.name, candidate.domain, candidate.condition)
        if key in existing_keys:
            skipped += 1
            continue
        created.append(create_rule(session, candidate))
        existing_keys.add(key)
    return DomainRulePackImportResult(
        pack_id=pack.pack_id,
        created_count=len(created),
        skipped_existing_count=skipped,
        rules=created,
    )


def _build_pack(pack_id: DomainRulePackId) -> DomainRulePack:
    if pack_id == DomainRulePackId.RETURNER_RECOVERY:
        rules = _returner_rules()
        return DomainRulePack(
            pack_id=pack_id,
            title="Reviewed Returner Recovery Rules",
            domain=KnowledgeDomain.RETURNER,
            summary="Prioritize low-friction recovery actions before expensive or group-dependent goals.",
            evidence_refs=["docs/knowledge_base/README.md"],
            rules=rules,
        )
    if pack_id == DomainRulePackId.BUILD_FIT_FRESHNESS:
        rules = _build_rules()
        return DomainRulePack(
            pack_id=pack_id,
            title="Reviewed Build Fit And Freshness Rules",
            domain=KnowledgeDomain.BUILD,
            summary="Explain build readiness through reusable gear, transition cost, source attribution, and patch freshness.",
            evidence_refs=["docs/knowledge_base/build/build_fit_rules.md"],
            rules=rules,
        )
    rules = _market_rules()
    for rule in rules:
        validate_market_language(rule.recommendation)
        validate_market_language(rule.explanation_template)
    return DomainRulePack(
        pack_id=pack_id,
        title="Reviewed Market Retention Rules",
        domain=KnowledgeDomain.MARKET,
        summary="Keep market guidance observational, goal-aware, and bounded to manual planning.",
        evidence_refs=["docs/knowledge_base/market/market_language_policy.md"],
        rules=rules,
    )


def _returner_rules() -> list[KnowledgeRuleInput]:
    evidence = ["docs/knowledge_base/README.md#returner-account-diagnosis"]
    return [
        KnowledgeRuleInput(
            name="Returner achievement recovery first",
            domain=KnowledgeDomain.RETURNER,
            condition="article_links_any_entity:gw2:achievement:aurora_step_x",
            recommendation="Review collection and achievement steps before committing to advanced goal work.",
            action_type=ActionType.COMPLETE_ACHIEVEMENT.value,
            priority_delta=0.22,
            explanation_template="For returning accounts, achievement recovery reduces confusion and makes later legendary planning easier to verify.",
            evidence_refs=evidence,
            confidence=0.82,
            review_status=KnowledgeReviewStatus.REVIEWED,
            enabled=False,
        ),
        KnowledgeRuleInput(
            name="Returner daily route stabilization",
            domain=KnowledgeDomain.RETURNER,
            condition="article_links_any_entity:gw2:task:bitterfrost_daily",
            recommendation="Use repeatable daily routes as a low-friction way to rebuild routine and gather goal materials.",
            action_type=ActionType.DO_DAILY.value,
            priority_delta=0.18,
            explanation_template="A stable daily route is easier to sustain than a broad catch-up plan and keeps recommendations grounded in visible tasks.",
            evidence_refs=evidence,
            confidence=0.8,
            review_status=KnowledgeReviewStatus.REVIEWED,
            enabled=False,
        ),
    ]


def _build_rules() -> list[KnowledgeRuleInput]:
    evidence = ["docs/knowledge_base/build/build_fit_rules.md"]
    return [
        KnowledgeRuleInput(
            name="Build source freshness warning",
            domain=KnowledgeDomain.BUILD,
            condition="article_links_any_entity:gw2:task:bitterfrost_daily",
            recommendation="Preserve build source attribution and warn when patch freshness is uncertain.",
            action_type=ActionType.DO_DAILY.value,
            priority_delta=0.16,
            explanation_template="Build advice should separate account readiness from source freshness so users can manually verify current patch suitability.",
            evidence_refs=evidence,
            confidence=0.84,
            review_status=KnowledgeReviewStatus.REVIEWED,
            enabled=False,
        ),
        KnowledgeRuleInput(
            name="Build transition cost before optimization",
            domain=KnowledgeDomain.BUILD,
            condition="article_links_any_entity:gw2:item:mystic_coin",
            recommendation="Explain reusable gear and transition cost before recommending expensive optimization paths.",
            action_type=ActionType.HOLD.value,
            priority_delta=0.14,
            explanation_template="Build Fit Advisor should prefer practical account fit and budget alternatives over unsupported performance claims.",
            evidence_refs=evidence,
            confidence=0.82,
            review_status=KnowledgeReviewStatus.REVIEWED,
            enabled=False,
        ),
    ]


def _market_rules() -> list[KnowledgeRuleInput]:
    evidence = ["docs/knowledge_base/market/market_language_policy.md"]
    return [
        KnowledgeRuleInput(
            name="Market observe before manual purchase",
            domain=KnowledgeDomain.MARKET,
            condition="article_links_any_entity:gw2:item:mystic_clover",
            recommendation="Observe price and acquisition context before any manual purchase decision.",
            action_type=ActionType.WATCH_PRICE.value,
            priority_delta=0.2,
            explanation_template="Market Radar guidance is planning support only and should frame price movement as evidence for manual review.",
            evidence_refs=evidence,
            confidence=0.86,
            review_status=KnowledgeReviewStatus.REVIEWED,
            enabled=False,
        ),
        KnowledgeRuleInput(
            name="Market protect active goal materials",
            domain=KnowledgeDomain.MARKET,
            condition="article_links_any_entity:gw2:item:mystic_coin",
            recommendation="Hold quantities needed by active goals before considering surplus decisions.",
            action_type=ActionType.HOLD.value,
            priority_delta=0.24,
            explanation_template="Goal-required materials should stay protected until the planner verifies that only true surplus remains.",
            evidence_refs=evidence,
            confidence=0.88,
            review_status=KnowledgeReviewStatus.REVIEWED,
            enabled=False,
        ),
    ]


def _rule_key(name: str, domain: KnowledgeDomain, condition: str) -> tuple[str, str, str]:
    return (name.strip().lower(), domain.value, condition.strip().lower())
