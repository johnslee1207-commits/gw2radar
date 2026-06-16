from pathlib import Path

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


def extract_priority_pdf_text(records: list[PdfSourceRecord], repo_root: Path, output_root: Path) -> list[Path]:
    extracted: list[Path] = []
    for record in records:
        if record.priority not in {"P0", "P1"}:
            continue
        source_path = repo_root / record.path
        output_path = output_root / f"{_safe_file_id(record.pdf_id)}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = extract_pdf_text(source_path)
        output_path.write_text(text, encoding="utf-8")
        extracted.append(output_path)
    return extracted


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF text extraction.") from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(f"\n\n--- page {index} ---\n{page_text.strip()}")
    return "\n".join(pages).strip() + "\n"


def _safe_file_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()
