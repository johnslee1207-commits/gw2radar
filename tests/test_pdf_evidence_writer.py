from gw2radar.kb_pdf.pdf_evidence_writer import build_evidence_records
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


def test_pdf_evidence_contains_source_file_hash_size_and_category() -> None:
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

    evidence = build_evidence_records([source])[0]

    assert evidence.evidence_id == "evidence:pdf:api:v2"
    assert evidence.source_type == "downloaded_pdf"
    assert evidence.source_file == source.path
    assert evidence.file_size == source.size_bytes
    assert evidence.sha256 == source.sha256
    assert evidence.category == "official_api"
    assert evidence.confidence == 0.95
