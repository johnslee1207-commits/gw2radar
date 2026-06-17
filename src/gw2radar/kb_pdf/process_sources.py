from pathlib import Path

from gw2radar.acquisition.local_pdf_adapter import ingest_pdf_inventory_as_acquisition_sources
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb_pdf.pdf_evidence_writer import build_evidence_records, write_evidence_jsonl
from gw2radar.kb_pdf.pdf_inventory import build_inventory, organize_pdf_sources, write_inventory_csv
from gw2radar.kb_pdf.pdf_kb_summarizer import write_initial_kb_summaries
from gw2radar.kb_pdf.pdf_text_extractor import extract_priority_pdf_text
from gw2radar.kb_pdf.official_news_summarizer import write_official_news_summaries, build_official_news_summaries


def process_downloaded_pdf_sources(repo_root: Path = Path(".")) -> dict[str, int]:
    repo_root = repo_root.resolve()
    flat_source_dir = repo_root / "docs" / "knowledge_base" / "official"
    source_root = repo_root / "docs" / "knowledge_base" / "_sources" / "pdf"
    inventory_path = repo_root / "data" / "kb" / "pdf_inventory.csv"
    evidence_path = repo_root / "data" / "kb" / "pdf_evidence.jsonl"
    extracted_root = repo_root / "data" / "extracted" / "pdf_text"
    official_summary_dir = repo_root / "docs" / "knowledge_base" / "official"
    official_news_dir = repo_root / "docs" / "knowledge_base" / "news" / "official"

    moved = organize_pdf_sources(flat_source_dir, source_root)
    records = build_inventory(repo_root, source_root)
    write_inventory_csv(records, inventory_path)
    write_evidence_jsonl(build_evidence_records(records), evidence_path)
    extracted = extract_priority_pdf_text(records, repo_root, extracted_root)
    summaries = write_initial_kb_summaries(records, official_summary_dir)
    news_summaries = write_official_news_summaries(build_official_news_summaries(records), official_news_dir)
    init_db()
    with db_session.SessionLocal() as session:
        acquisition_result = ingest_pdf_inventory_as_acquisition_sources(session, records)

    return {
        "moved_pdf_count": len(moved),
        "inventory_count": len(records),
        "extracted_text_count": len(extracted),
        "summary_count": len(summaries),
        "news_summary_count": len(news_summaries),
        "acquisition_source_count": acquisition_result.source_count,
        "new_acquisition_source_count": acquisition_result.new_source_count,
        "raw_evidence_count": acquisition_result.evidence_count,
        "new_raw_evidence_count": acquisition_result.new_evidence_count,
        "acquisition_job_count": acquisition_result.job_count,
    }


def main() -> None:
    stats = process_downloaded_pdf_sources(Path("."))
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
