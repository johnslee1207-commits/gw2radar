import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


@dataclass(frozen=True)
class OfficialNewsSummary:
    news_id: str
    title: str
    source_pdf: str
    evidence_id: str
    summary: str
    source_type: str
    affected_systems: list[str]
    possible_product_context: list[str]
    confidence: float
    review_status: str


def load_inventory_csv(path: Path) -> list[PdfSourceRecord]:
    with path.open(encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return [
            PdfSourceRecord(
                pdf_id=row["pdf_id"],
                file_name=row["file_name"],
                path=row["path"],
                size_bytes=int(row["size_bytes"]),
                category=row["category"],
                year=int(row["year"]) if row["year"] else None,
                priority=row["priority"],
                status=row["status"],
                sha256=row["sha256"],
            )
            for row in rows
        ]


def build_official_news_summaries(records: list[PdfSourceRecord]) -> list[OfficialNewsSummary]:
    summaries: list[OfficialNewsSummary] = []
    for record in records:
        if record.category != "official_news":
            continue
        title = _title_from_file_name(record.file_name)
        summaries.append(
            OfficialNewsSummary(
                news_id=record.pdf_id.replace("pdf:", "news:", 1),
                title=title,
                source_pdf=record.path,
                evidence_id=record.pdf_id.replace("pdf:", "evidence:pdf:", 1),
                summary=(
                    f"Structured draft source note for official Guild Wars 2 news item: {title}. "
                    "Use source evidence for verification before making product or gameplay claims."
                ),
                source_type="official_news",
                affected_systems=_affected_systems_for(title),
                possible_product_context=["needs_manual_review"],
                confidence=0.75,
                review_status="draft",
            )
        )
    return sorted(summaries, key=lambda item: item.title.lower())


def write_official_news_summaries(summaries: list[OfficialNewsSummary], output_root: Path) -> list[Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used_names: set[str] = set()
    for summary in summaries:
        file_name = _unique_name(_slug(summary.title), used_names)
        output_path = output_root / f"{file_name}.md"
        output_path.write_text(render_official_news_summary(summary), encoding="utf-8")
        written.append(output_path)
    return written


def render_official_news_summary(summary: OfficialNewsSummary) -> str:
    lines = [
        "---",
        f"title: {summary.title}",
        "domain: official",
        "content_type: summary",
        f"summary: {summary.summary}",
        "source_refs:",
        "linked_entities: gw2:system:official_news",
        "linked_actions: INGEST_SOURCE",
        f"confidence: {summary.confidence}",
        f"review_status: {summary.review_status}",
        "---",
        "",
        f"# {summary.title}",
        "",
        f"- news_id: `{summary.news_id}`",
        f"- source_type: `{summary.source_type}`",
        f"- source_pdf: `{summary.source_pdf}`",
        f"- evidence_id: `{summary.evidence_id}`",
        f"- confidence: `{summary.confidence:.2f}`",
        f"- review_status: `{summary.review_status}`",
        "",
        "## Structured News Fields",
        "",
        *_field_lines("affected_systems", summary.affected_systems),
        *_field_lines("possible_product_context", summary.possible_product_context),
        "",
        "## Review Boundary",
        "",
        "- This is a structured source stub generated from the downloaded PDF inventory.",
        "- It does not copy full official news text.",
        "- Promote facts only after manual review of the source artifact.",
        "",
    ]
    return "\n".join(lines)


def generate_official_news_summaries(
    inventory_path: Path = Path("data") / "kb" / "pdf_inventory.csv",
    output_root: Path = Path("docs") / "knowledge_base" / "news" / "official",
) -> dict[str, int]:
    records = load_inventory_csv(inventory_path)
    summaries = build_official_news_summaries(records)
    written = write_official_news_summaries(summaries, output_root)
    return {"summary_count": len(written)}


def main() -> None:
    stats = generate_official_news_summaries()
    for key, value in stats.items():
        print(f"{key}: {value}")


def _title_from_file_name(file_name: str) -> str:
    title = Path(file_name).stem
    title = title.replace(" - GuildWars2.com", "").replace(" – GuildWars2.com", "")
    title = title.replace("_", ": ")
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    return " ".join(normalized.split()) or "Official GW2 News Source"


def _affected_systems_for(title: str) -> list[str]:
    lower = title.lower()
    systems = ["official_news"]
    if "sale" in lower or "discount" in lower or "gem store" in lower:
        systems.append("commerce_context")
    if "raid" in lower:
        systems.append("group_content")
    if "wvw" in lower:
        systems.append("wvw")
    if "story" in lower or "chapter" in lower:
        systems.append("story")
    if "beta" in lower:
        systems.append("beta")
    return systems


def _field_lines(name: str, values: list[str]) -> list[str]:
    if not values:
        return [f"- {name}: []"]
    rendered = ", ".join(f"`{value}`" for value in values)
    return [f"- {name}: [{rendered}]"]


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = "_".join(
        part for part in "".join(ch.lower() if ch.isalnum() else "_" for ch in normalized).split("_") if part
    )
    return slug or "official_gw2_news"


def _unique_name(base: str, used_names: set[str]) -> str:
    candidate = base
    index = 2
    while candidate in used_names:
        candidate = f"{base}_{index}"
        index += 1
    used_names.add(candidate)
    return candidate


if __name__ == "__main__":
    main()
