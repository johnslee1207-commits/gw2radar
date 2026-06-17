import csv
import re
from io import StringIO
from pathlib import Path

from pydantic import BaseModel, Field

from gw2radar.kb.kb_models import KnowledgeContentType, KnowledgeDomain, KnowledgeReviewStatus, validate_kb_text


STRUCTURED_LIST_RE = re.compile(r"^- (?P<name>[a-zA-Z0-9_]+): \[(?P<values>.*)\]$", re.MULTILINE)
BACKTICK_VALUE_RE = re.compile(r"`([^`]+)`")
EVIDENCE_RE = re.compile(r"`(evidence:[^`]+)`")


class SourceSemanticHint(BaseModel):
    source_path: str
    source_kind: str
    title: str
    domain: KnowledgeDomain
    content_type: KnowledgeContentType
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    linked_entities: list[str] = Field(default_factory=list)
    linked_actions: list[str] = Field(default_factory=list)
    ontology_links: list[str] = Field(default_factory=list)
    action_hints: list[str] = Field(default_factory=list)
    structured_fields: dict[str, list[str]] = Field(default_factory=dict)
    confidence: float
    review_status: KnowledgeReviewStatus
    blockers: list[str] = Field(default_factory=list)


class SourceSemanticExtractionReport(BaseModel):
    schema_version: str
    source_root: str
    hint_count: int
    blocker_count: int
    source_kind_counts: dict[str, int]
    ontology_link_count: int
    action_hint_count: int
    hints: list[SourceSemanticHint]
    blockers: list[str]


def build_source_semantic_report(
    source_root: Path = Path("docs") / "knowledge_base",
    *,
    limit: int | None = None,
) -> SourceSemanticExtractionReport:
    resolved = source_root.resolve()
    hints: list[SourceSemanticHint] = []
    for path in _iter_source_markdown(resolved):
        hints.append(extract_source_semantic_hint(path, resolved))
        if limit is not None and len(hints) >= limit:
            break
    blockers = [f"{hint.source_path}: {blocker}" for hint in hints for blocker in hint.blockers]
    source_kind_counts: dict[str, int] = {}
    for hint in hints:
        source_kind_counts[hint.source_kind] = source_kind_counts.get(hint.source_kind, 0) + 1
    return SourceSemanticExtractionReport(
        schema_version="gw2radar.kb_source_semantics.v1",
        source_root=str(resolved),
        hint_count=len(hints),
        blocker_count=len(blockers),
        source_kind_counts=source_kind_counts,
        ontology_link_count=sum(len(hint.ontology_links) for hint in hints),
        action_hint_count=sum(len(hint.action_hints) for hint in hints),
        hints=hints,
        blockers=blockers,
    )


def extract_source_semantic_hint(path: Path, root: Path | None = None) -> SourceSemanticHint:
    text = path.read_text(encoding="utf-8")
    metadata, body = _parse_front_matter(text)
    blockers: list[str] = []
    try:
        validate_kb_text(metadata.get("summary", ""), body)
    except ValueError as exc:
        blockers.append(str(exc))
    if len(body) > 8000:
        blockers.append("Source summary body is too long for summary-only extraction.")

    structured = _structured_fields(body)
    linked_entities = _csv(metadata.get("linked_entities", ""))
    linked_actions = _csv(metadata.get("linked_actions", ""))
    evidence_refs = sorted(set(_csv(metadata.get("source_refs", "")) + EVIDENCE_RE.findall(body)))
    ontology_links = sorted(set(linked_entities + _ontology_from_structured_fields(structured)))
    action_hints = sorted(set(linked_actions + _action_hints_from_structured_fields(structured)))
    if not evidence_refs:
        blockers.append("No evidence reference found in source summary.")
    if not ontology_links:
        blockers.append("No ontology links inferred from source summary.")

    source_path = str(path.resolve())
    if root is not None:
        try:
            source_path = str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            source_path = str(path.resolve())
    return SourceSemanticHint(
        source_path=source_path.replace("\\", "/"),
        source_kind=_source_kind(path, structured, linked_entities),
        title=_required(metadata, "title", blockers),
        domain=KnowledgeDomain(_required(metadata, "domain", blockers) or KnowledgeDomain.OFFICIAL.value),
        content_type=KnowledgeContentType(_required(metadata, "content_type", blockers) or KnowledgeContentType.SUMMARY.value),
        summary=_required(metadata, "summary", blockers),
        evidence_refs=evidence_refs,
        linked_entities=linked_entities,
        linked_actions=linked_actions,
        ontology_links=ontology_links,
        action_hints=action_hints,
        structured_fields=structured,
        confidence=float(metadata.get("confidence", "0.6") or "0.6"),
        review_status=KnowledgeReviewStatus(metadata.get("review_status", "draft") or "draft"),
        blockers=blockers,
    )


def render_source_semantic_report_markdown(report: SourceSemanticExtractionReport) -> str:
    lines = [
        "# Official Source Semantic Extraction",
        "",
        f"- schema_version: `{report.schema_version}`",
        f"- source_root: `{report.source_root}`",
        f"- hint_count: `{report.hint_count}`",
        f"- blocker_count: `{report.blocker_count}`",
        f"- ontology_link_count: `{report.ontology_link_count}`",
        f"- action_hint_count: `{report.action_hint_count}`",
        "",
        "## Source Kinds",
        "",
        "| Source Kind | Count |",
        "|---|---:|",
    ]
    for source_kind, count in sorted(report.source_kind_counts.items()):
        lines.append(f"| {source_kind} | {count} |")
    lines.extend(
        [
            "",
            "## Hints",
            "",
            "| Source | Kind | Ontology Links | Action Hints | Evidence | Blockers |",
            "|---|---|---|---|---|---|",
        ]
    )
    for hint in report.hints:
        lines.append(
            f"| {hint.source_path} | {hint.source_kind} | {_join(hint.ontology_links)} | "
            f"{_join(hint.action_hints)} | {_join(hint.evidence_refs)} | {_join(hint.blockers)} |"
        )
    if report.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend([f"- {blocker}" for blocker in report.blockers])
    return "\n".join(lines).strip() + "\n"


def render_source_semantic_report_csv(report: SourceSemanticExtractionReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["source_path", "source_kind", "ontology_links", "action_hints", "evidence_refs", "blockers"])
    for hint in report.hints:
        writer.writerow(
            [
                hint.source_path,
                hint.source_kind,
                "; ".join(hint.ontology_links),
                "; ".join(hint.action_hints),
                "; ".join(hint.evidence_refs),
                "; ".join(hint.blockers),
            ]
        )
    return output.getvalue()


def _iter_source_markdown(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        raise ValueError("Knowledge source root not found.")
    paths: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        rel_parts = path.relative_to(root).parts
        if path.name.upper() == "README.MD" or "source_registry" in rel_parts:
            continue
        if rel_parts and rel_parts[0] in {"official", "news", "patch_notes"}:
            paths.append(path)
    return paths


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("Knowledge source Markdown must start with front matter.")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("Knowledge source Markdown front matter is not closed.")
    raw_meta = text[4:end]
    body = text[end + 5 :]
    metadata: dict[str, str] = {}
    for line in raw_meta.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, body


def _structured_fields(body: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for match in STRUCTURED_LIST_RE.finditer(body):
        raw_values = match.group("values")
        fields[match.group("name")] = BACKTICK_VALUE_RE.findall(raw_values)
    return fields


def _ontology_from_structured_fields(fields: dict[str, list[str]]) -> list[str]:
    links: list[str] = []
    for value in fields.get("affected_systems", []):
        links.append(f"gw2:system:{value}")
    for field in ("changed_professions", "changed_skills", "changed_traits", "changed_items", "changed_rewards"):
        for value in fields.get(field, []):
            links.append(f"gw2:{field.removeprefix('changed_')[:-1]}:{_slug(value)}")
    endpoint = fields.get("primary_entities", [])
    links.extend(endpoint)
    return links


def _action_hints_from_structured_fields(fields: dict[str, list[str]]) -> list[str]:
    hints: list[str] = []
    if fields.get("possible_build_impact"):
        hints.append("review_build_freshness")
    if fields.get("possible_market_impact"):
        hints.append("review_market_watchlist")
    if fields.get("possible_product_context"):
        hints.append("review_product_context")
    hints.extend(fields.get("primary_actions", []))
    return hints


def _source_kind(path: Path, fields: dict[str, list[str]], linked_entities: list[str]) -> str:
    parts = {part.lower() for part in path.parts}
    if "patch_notes" in parts:
        return "patch_note_summary"
    if "news" in parts:
        return "official_news_summary"
    if any(entity.startswith("api_endpoint:") for entity in linked_entities) or fields.get("primary_entities"):
        return "official_api_endpoint_summary"
    return "official_source_summary"


def _required(metadata: dict[str, str], key: str, blockers: list[str]) -> str:
    value = metadata.get(key, "").strip()
    if not value:
        blockers.append(f"Missing required source metadata: {key}.")
    return value


def _csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _join(values: list[str]) -> str:
    return "; ".join(values) if values else "none"


def _slug(value: str) -> str:
    return "_".join(part for part in "".join(ch.lower() if ch.isalnum() else "_" for ch in value).split("_") if part)
