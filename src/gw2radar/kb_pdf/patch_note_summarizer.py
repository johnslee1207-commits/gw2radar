import csv
from dataclasses import dataclass
from pathlib import Path

from gw2radar.kb_pdf.pdf_classifier import extract_patch_date
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


@dataclass(frozen=True)
class PatchNoteSummary:
    patch_id: str
    date: str
    year: int
    source_pdf: str
    evidence_id: str
    summary: str
    changed_professions: list[str]
    changed_skills: list[str]
    changed_traits: list[str]
    changed_items: list[str]
    changed_rewards: list[str]
    affected_systems: list[str]
    possible_build_impact: list[str]
    possible_market_impact: list[str]
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


def build_recent_patch_summaries(records: list[PdfSourceRecord]) -> list[PatchNoteSummary]:
    summaries: list[PatchNoteSummary] = []
    for record in records:
        if record.category != "patch_note" or record.priority != "P2" or record.year is None:
            continue
        patch_date = extract_patch_date(record.file_name)
        if patch_date is None:
            continue
        summaries.append(
            PatchNoteSummary(
                patch_id=f"patch:{patch_date}",
                date=patch_date,
                year=record.year,
                source_pdf=record.path,
                evidence_id=record.pdf_id.replace("pdf:", "evidence:pdf:", 1),
                summary=_summary_for(record),
                changed_professions=[],
                changed_skills=[],
                changed_traits=[],
                changed_items=[],
                changed_rewards=[],
                affected_systems=_affected_systems_for(record.file_name),
                possible_build_impact=["needs_manual_review"],
                possible_market_impact=["needs_manual_review"],
                confidence=0.65,
                review_status="draft",
            )
        )
    return sorted(summaries, key=lambda item: item.date, reverse=True)


def write_patch_note_summaries(summaries: list[PatchNoteSummary], output_root: Path) -> list[Path]:
    written: list[Path] = []
    for summary in summaries:
        output_dir = output_root / str(summary.year)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{summary.date}.md"
        output_path.write_text(render_patch_note_summary(summary), encoding="utf-8")
        written.append(output_path)
    return written


def render_patch_note_summary(summary: PatchNoteSummary) -> str:
    lines = [
        "---",
        f"title: GW2 Patch Note {summary.date}",
        "domain: official",
        "content_type: summary",
        f"summary: {summary.summary}",
        "source_refs:",
        "linked_entities: gw2:system:patch_notes",
        "linked_actions: INGEST_SOURCE",
        f"confidence: {summary.confidence}",
        f"review_status: {summary.review_status}",
        "---",
        "",
        f"# GW2 Patch Note {summary.date}",
        "",
        f"- patch_id: `{summary.patch_id}`",
        f"- date: `{summary.date}`",
        f"- source_pdf: `{summary.source_pdf}`",
        f"- evidence_id: `{summary.evidence_id}`",
        f"- confidence: `{summary.confidence:.2f}`",
        f"- review_status: `{summary.review_status}`",
        "",
        "## Structured Impact Fields",
        "",
        *_field_lines("changed_professions", summary.changed_professions),
        *_field_lines("changed_skills", summary.changed_skills),
        *_field_lines("changed_traits", summary.changed_traits),
        *_field_lines("changed_items", summary.changed_items),
        *_field_lines("changed_rewards", summary.changed_rewards),
        *_field_lines("affected_systems", summary.affected_systems),
        *_field_lines("possible_build_impact", summary.possible_build_impact),
        *_field_lines("possible_market_impact", summary.possible_market_impact),
        "",
        "## Review Boundary",
        "",
        "- This is a structured source stub generated from the downloaded PDF inventory.",
        "- It does not copy full patch-note text.",
        "- Promote individual impact fields only after manual review of the source artifact.",
        "",
    ]
    return "\n".join(lines)


def generate_recent_patch_note_summaries(
    inventory_path: Path = Path("data") / "kb" / "pdf_inventory.csv",
    output_root: Path = Path("docs") / "knowledge_base" / "patch_notes",
) -> dict[str, int]:
    records = load_inventory_csv(inventory_path)
    summaries = build_recent_patch_summaries(records)
    written = write_patch_note_summaries(summaries, output_root)
    return {"summary_count": len(written)}


def main() -> None:
    stats = generate_recent_patch_note_summaries()
    for key, value in stats.items():
        print(f"{key}: {value}")


def _summary_for(record: PdfSourceRecord) -> str:
    patch_date = extract_patch_date(record.file_name) or "unknown date"
    return (
        f"Structured draft summary for the official GW2 patch note dated {patch_date}; "
        "impact fields require manual review before use in recommendations."
    )


def _affected_systems_for(file_name: str) -> list[str]:
    lower = file_name.lower()
    systems = ["patch_notes"]
    if "release notes" in lower:
        systems.append("release_notes")
    if "game update notes" in lower:
        systems.append("game_update")
    return systems


def _field_lines(name: str, values: list[str]) -> list[str]:
    if not values:
        return [f"- {name}: []"]
    rendered = ", ".join(f"`{value}`" for value in values)
    return [f"- {name}: [{rendered}]"]


if __name__ == "__main__":
    main()
