import json
from dataclasses import asdict, dataclass
from pathlib import Path

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


@dataclass(frozen=True)
class PdfEvidenceRecord:
    evidence_id: str
    source_type: str
    source_file: str
    original_url: str | None
    downloaded_at: str
    sha256: str
    file_size: int
    category: str
    confidence: float


def build_evidence_records(records: list[PdfSourceRecord]) -> list[PdfEvidenceRecord]:
    return [
        PdfEvidenceRecord(
            evidence_id=record.pdf_id.replace("pdf:", "evidence:pdf:", 1),
            source_type="downloaded_pdf",
            source_file=record.path,
            original_url=None,
            downloaded_at="2026-06-16",
            sha256=record.sha256,
            file_size=record.size_bytes,
            category=record.category,
            confidence=_confidence_for_category(record.category),
        )
        for record in records
    ]


def write_evidence_jsonl(records: list[PdfEvidenceRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")


def _confidence_for_category(category: str) -> float:
    if category in {"official_api", "official_api_endpoint", "api_governance", "api_permission", "api_key"}:
        return 0.95
    if category == "official_news":
        return 0.9
    if category == "arenanet_policy":
        return 0.9
    if category == "patch_note":
        return 0.85
    if category == "wiki_meta":
        return 0.7
    return 0.4
