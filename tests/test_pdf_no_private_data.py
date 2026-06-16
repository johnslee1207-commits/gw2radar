import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord
from gw2radar.kb_pdf.pdf_kb_summarizer import write_initial_kb_summaries


def test_pdf_generated_kb_files_do_not_include_private_markers() -> None:
    temp_dir = Path(".test_tmp") / f"pdf-private-{uuid4().hex}"
    try:
        source = PdfSourceRecord(
            pdf_id="pdf:api:key",
            file_name="API_API key - Guild Wars 2 Wiki (GW2W).pdf",
            path="docs/knowledge_base/_sources/pdf/official_api/API_API key - Guild Wars 2 Wiki (GW2W).pdf",
            size_bytes=248792,
            category="api_key",
            year=None,
            priority="P0",
            status="pending",
            sha256="b" * 64,
        )

        written = write_initial_kb_summaries([source], temp_dir)
        combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in written)

        assert "12345678-1234-1234-1234-123456789abc" not in combined
        assert "raw private account payload" not in combined
        assert "private player payloads" in combined
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
