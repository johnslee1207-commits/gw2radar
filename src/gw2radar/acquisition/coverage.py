from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import AcquisitionSourceModel, KnowledgeArticleModel, KnowledgeRuleModel, RawEvidenceModel


class EvidenceCoverageSourceRow(BaseModel):
    source_id: str
    name: str
    source_type: str
    raw_evidence_count: int
    kb_article_count: int
    knowledge_rule_count: int
    coverage_status: str
    gaps: list[str] = Field(default_factory=list)


class EvidenceCoverageMap(BaseModel):
    schema_version: str = "gw2radar.acquisition_evidence_coverage.v1"
    source_count: int
    raw_evidence_count: int
    kb_article_count: int
    knowledge_rule_count: int
    covered_source_count: int
    source_rows: list[EvidenceCoverageSourceRow]
    orphan_raw_evidence_ids: list[str] = Field(default_factory=list)
    rule_ids_without_raw_evidence: list[str] = Field(default_factory=list)
    next_priorities: list[str] = Field(default_factory=list)


def build_evidence_coverage_map(session: Session) -> EvidenceCoverageMap:
    sources = session.query(AcquisitionSourceModel).order_by(AcquisitionSourceModel.name).all()
    evidence = session.query(RawEvidenceModel).all()
    articles = session.query(KnowledgeArticleModel).all()
    rules = session.query(KnowledgeRuleModel).all()

    evidence_by_source: dict[str, list[RawEvidenceModel]] = {}
    evidence_by_id: dict[str, RawEvidenceModel] = {}
    for item in evidence:
        evidence_by_source.setdefault(item.source_id, []).append(item)
        evidence_by_id[item.evidence_id] = item

    source_ids = {source.source_id for source in sources}
    article_refs_by_source = {source_id: 0 for source_id in source_ids}
    for article in articles:
        for ref in article.source_refs_json or []:
            if ref in article_refs_by_source:
                article_refs_by_source[ref] += 1

    rule_refs_by_source = {source_id: 0 for source_id in source_ids}
    rules_without_raw: list[str] = []
    for rule in rules:
        refs = rule.evidence_refs_json or []
        raw_refs = [ref for ref in refs if ref in evidence_by_id]
        source_refs = [evidence_by_id[ref].source_id for ref in raw_refs]
        for source_id in source_refs:
            if source_id in rule_refs_by_source:
                rule_refs_by_source[source_id] += 1
        if refs and not raw_refs:
            rules_without_raw.append(rule.rule_id)

    rows = [
        _source_row(
            source,
            raw_evidence_count=len(evidence_by_source.get(source.source_id, [])),
            kb_article_count=article_refs_by_source.get(source.source_id, 0),
            knowledge_rule_count=rule_refs_by_source.get(source.source_id, 0),
        )
        for source in sources
    ]
    orphan_evidence = [item.evidence_id for item in evidence if item.source_id not in source_ids]
    priorities = _next_priorities(rows, orphan_evidence, rules_without_raw)
    return EvidenceCoverageMap(
        source_count=len(sources),
        raw_evidence_count=len(evidence),
        kb_article_count=len(articles),
        knowledge_rule_count=len(rules),
        covered_source_count=sum(1 for row in rows if row.coverage_status == "covered"),
        source_rows=rows,
        orphan_raw_evidence_ids=sorted(orphan_evidence),
        rule_ids_without_raw_evidence=sorted(rules_without_raw),
        next_priorities=priorities,
    )


def render_evidence_coverage_markdown(report: EvidenceCoverageMap) -> str:
    lines = [
        "# Acquisition Evidence Coverage Map",
        "",
        f"- schema_version: `{report.schema_version}`",
        f"- sources: `{report.source_count}`",
        f"- raw_evidence: `{report.raw_evidence_count}`",
        f"- kb_articles: `{report.kb_article_count}`",
        f"- knowledge_rules: `{report.knowledge_rule_count}`",
        f"- covered_sources: `{report.covered_source_count}`",
        "",
        "## Source Coverage",
        "",
        "| Source | Type | Raw Evidence | KB Articles | Rules | Status | Gaps |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in report.source_rows:
        gaps = "; ".join(row.gaps) if row.gaps else "none"
        lines.append(
            f"| {row.name} | {row.source_type} | {row.raw_evidence_count} | "
            f"{row.kb_article_count} | {row.knowledge_rule_count} | {row.coverage_status} | {gaps} |"
        )
    lines.extend(["", "## Orphans And Gaps", ""])
    lines.append(
        "- orphan_raw_evidence_ids: "
        + ("; ".join(report.orphan_raw_evidence_ids) if report.orphan_raw_evidence_ids else "none")
    )
    lines.append(
        "- rule_ids_without_raw_evidence: "
        + ("; ".join(report.rule_ids_without_raw_evidence) if report.rule_ids_without_raw_evidence else "none")
    )
    lines.extend(["", "## Next Priorities", ""])
    if report.next_priorities:
        lines.extend(f"- {priority}" for priority in report.next_priorities)
    else:
        lines.append("- Maintain evidence import, KB linking, and rule evidence review cadence.")
    return "\n".join(lines) + "\n"


def _source_row(
    source: AcquisitionSourceModel,
    *,
    raw_evidence_count: int,
    kb_article_count: int,
    knowledge_rule_count: int,
) -> EvidenceCoverageSourceRow:
    gaps: list[str] = []
    if raw_evidence_count == 0:
        gaps.append("source_without_raw_evidence")
    if kb_article_count == 0:
        gaps.append("source_without_kb_article")
    if raw_evidence_count and knowledge_rule_count == 0:
        gaps.append("raw_evidence_not_used_by_rule")
    if raw_evidence_count and kb_article_count:
        status = "covered" if knowledge_rule_count else "evidence_linked"
    elif raw_evidence_count:
        status = "evidence_only"
    elif kb_article_count:
        status = "kb_only"
    else:
        status = "uncovered"
    return EvidenceCoverageSourceRow(
        source_id=source.source_id,
        name=source.name,
        source_type=source.source_type,
        raw_evidence_count=raw_evidence_count,
        kb_article_count=kb_article_count,
        knowledge_rule_count=knowledge_rule_count,
        coverage_status=status,
        gaps=gaps,
    )


def _next_priorities(
    rows: list[EvidenceCoverageSourceRow],
    orphan_evidence: list[str],
    rules_without_raw: list[str],
) -> list[str]:
    priorities: list[str] = []
    if any(row.raw_evidence_count == 0 for row in rows):
        priorities.append("Import or generate raw evidence for uncovered acquisition sources.")
    if any(row.kb_article_count == 0 for row in rows):
        priorities.append("Link acquisition sources to reviewed KB articles.")
    if any(row.raw_evidence_count and row.knowledge_rule_count == 0 for row in rows):
        priorities.append("Distill reviewed raw evidence into KnowledgeRule candidates where appropriate.")
    if orphan_evidence:
        priorities.append("Resolve raw evidence rows whose source_id no longer exists.")
    if rules_without_raw:
        priorities.append("Attach raw evidence refs to KnowledgeRule records that currently cite only documents or notes.")
    return priorities[:5]
