import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord
from gw2radar.kb_pdf.pdf_kb_summarizer import write_initial_kb_summaries


def test_pdf_kb_summary_does_not_copy_full_text() -> None:
    temp_dir = Path(".test_tmp") / f"pdf-no-copy-{uuid4().hex}"
    try:
        source = PdfSourceRecord(
            pdf_id="pdf:api:v2",
            file_name="API_2 - Guild Wars 2 Wiki (GW2W).pdf",
            path="docs/knowledge_base/_sources/pdf/official_api/API_2 - Guild Wars 2 Wiki (GW2W).pdf",
            size_bytes=721484,
            category="official_api",
            year=None,
            priority="P0",
            status="pending",
            sha256="a" * 64,
        )
        forbidden_full_text = "This simulated source-only paragraph should never be copied into a KB article."

        written = write_initial_kb_summaries([source], temp_dir)
        combined = "\n".join(path.read_text(encoding="utf-8") for path in written)

        assert "full-text copy" in combined
        assert forbidden_full_text not in combined
        assert len(combined) < 4000
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
