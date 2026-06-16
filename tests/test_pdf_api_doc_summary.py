import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord
from gw2radar.kb_pdf.pdf_kb_summarizer import write_initial_kb_summaries


def test_pdf_api_endpoint_summary_uses_required_schema_fields() -> None:
    temp_dir = Path(".test_tmp") / f"pdf-api-summary-{uuid4().hex}"
    try:
        source = PdfSourceRecord(
            pdf_id="pdf:api_endpoint:account_wallet",
            file_name="API_2_account_wallet - Guild Wars 2 Wiki (GW2W).pdf",
            path="docs/knowledge_base/_sources/pdf/official_api/endpoints/API_2_account_wallet - Guild Wars 2 Wiki (GW2W).pdf",
            size_bytes=383942,
            category="official_api_endpoint",
            year=None,
            priority="P1",
            status="pending",
            sha256="c" * 64,
        )

        write_initial_kb_summaries([source], temp_dir)
        summary = (temp_dir / "api_endpoints" / "account_wallet.md").read_text(encoding="utf-8")

        assert "endpoint: `/v2/account/wallet`" in summary
        assert "requires_api_key: `true`" in summary
        assert "required_scopes: `account`" in summary
        assert "public_or_private_graph_layer: `private_player_state`" in summary
        assert "evidence_id: `evidence:pdf:api_endpoint:account_wallet`" in summary
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
