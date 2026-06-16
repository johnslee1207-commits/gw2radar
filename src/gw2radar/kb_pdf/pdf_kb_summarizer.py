from pathlib import Path

from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


SUMMARY_TARGETS = {
    "pdf:api:main": "gw2_api_summary.md",
    "pdf:api:v2": "api_v2_resource_model.md",
    "pdf:api:best_practices": "api_rate_limit.md",
    "pdf:api:tokeninfo": "api_scopes_and_tokeninfo.md",
    "pdf:api:key": "api_key_safety.md",
}

AREANET_SUMMARY_FILE = "arenanet_content_terms_summary.md"


def write_initial_kb_summaries(records: list[PdfSourceRecord], official_dir: Path) -> list[Path]:
    official_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    record_by_id = {record.pdf_id: record for record in records}

    for pdf_id, file_name in SUMMARY_TARGETS.items():
        record = record_by_id.get(pdf_id)
        if record is None:
            continue
        path = official_dir / file_name
        path.write_text(_render_official_summary(record, file_name), encoding="utf-8")
        written.append(path)

    arenanet_records = [record for record in records if record.category == "arenanet_policy"]
    if arenanet_records:
        path = official_dir / AREANET_SUMMARY_FILE
        path.write_text(_render_arenanet_summary(arenanet_records), encoding="utf-8")
        written.append(path)

    endpoint_dir = official_dir / "api_endpoints"
    endpoint_records = [record for record in records if record.category == "official_api_endpoint"]
    for record in sorted(endpoint_records, key=lambda item: item.file_name):
        path = endpoint_dir / f"{_endpoint_slug(record)}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_endpoint_summary(record), encoding="utf-8")
        written.append(path)

    return written


def _render_official_summary(record: PdfSourceRecord, output_name: str) -> str:
    title = {
        "gw2_api_summary.md": "GW2 API governed access summary",
        "api_v2_resource_model.md": "GW2 API v2 resource model summary",
        "api_rate_limit.md": "GW2 API rate limit and best-practice summary",
        "api_scopes_and_tokeninfo.md": "GW2 API scopes and tokeninfo summary",
        "api_key_safety.md": "GW2 API credential safety summary",
    }[output_name]
    linked_actions = {
        "gw2_api_summary.md": "REFRESH_PUBLIC_STATIC_DATA, SYNC_ACCOUNT_SNAPSHOT",
        "api_v2_resource_model.md": "INGEST_SOURCE, REFRESH_PUBLIC_STATIC_DATA",
        "api_rate_limit.md": "REFRESH_PUBLIC_STATIC_DATA",
        "api_scopes_and_tokeninfo.md": "VALIDATE_API_SCOPE, SYNC_ACCOUNT_SNAPSHOT",
        "api_key_safety.md": "VALIDATE_API_SCOPE",
    }[output_name]
    return "\n".join(
        [
            "---",
            f"title: {title}",
            "domain: official",
            "content_type: source_note",
            f"summary: Source-linked summary derived from {_safe_source_label(record)}; use the PDF evidence for verification and avoid copying full source text into KB articles.",
            "linked_entities: gw2:system:official_api",
            f"linked_actions: {linked_actions}",
            "source_refs:",
            "confidence: 0.95",
            "review_status: draft",
            "---",
            "",
            f"# {title}",
            "",
            f"- Evidence ID: `{record.pdf_id.replace('pdf:', 'evidence:pdf:', 1)}`",
            "- Source artifact: recorded in `data/kb/pdf_inventory.csv` and `data/kb/pdf_evidence.jsonl`.",
            f"- SHA256: `{record.sha256}`",
            "- Processing note: this article is a concise source summary, not a full-text copy of the PDF.",
            "- Governance boundary: no credentials, private player payloads, or unsupported claims are included.",
            "",
        ]
    )


def _render_arenanet_summary(records: list[PdfSourceRecord]) -> str:
    refs = [record.pdf_id.replace("pdf:", "evidence:pdf:", 1) for record in records]
    source_lines = [f"- `{record.file_name}` -> `{record.path}`" for record in sorted(records, key=lambda item: item.file_name)]
    return "\n".join(
        [
            "---",
            "title: ArenaNet content and security policy summary",
            "domain: official",
            "content_type: source_note",
            "summary: Source-linked ArenaNet policy summary for credential safety, account security, and content-use boundaries.",
            "linked_entities: gw2:system:official_api, gw2:system:privacy_boundary",
            "linked_actions: VALIDATE_API_SCOPE",
            "source_refs:",
            "confidence: 0.9",
            "review_status: draft",
            "---",
            "",
            "# ArenaNet Content And Security Policy Summary",
            "",
            "- Evidence IDs: " + ", ".join(f"`{ref}`" for ref in refs),
            "- Processing note: this summary references downloaded PDFs as evidence artifacts and does not copy full source text.",
            "- Security boundary: never store secrets in source code, and never include raw credentials or private player payloads in KB content.",
            "",
            "## Source Artifacts",
            *source_lines,
            "",
        ]
    )


def _render_endpoint_summary(record: PdfSourceRecord) -> str:
    endpoint = _endpoint_slug(record).replace("_", "/")
    public_private = _graph_layer_for_endpoint(endpoint)
    requires_key = "true" if public_private == "private_player_state" else "false"
    return "\n".join(
        [
            "---",
            f"title: GW2 API endpoint /v2/{endpoint}",
            "domain: official",
            "content_type: source_note",
            f"summary: Initial endpoint summary for /v2/{endpoint}; verify behavior against the source PDF before promotion to reviewed.",
            "source_refs:",
            f"linked_entities: api_endpoint:/v2/{endpoint}",
            "linked_actions: INGEST_SOURCE, VALIDATE_API_SCOPE",
            "confidence: 0.9",
            "review_status: draft",
            "---",
            "",
            f"# GW2 API Endpoint /v2/{endpoint}",
            "",
            f"- endpoint: `/v2/{endpoint}`",
            "- method: `GET`",
            f"- requires_api_key: `{requires_key}`",
            f"- required_scopes: `{_scopes_for_endpoint(endpoint)}`",
            f"- public_or_private_graph_layer: `{public_private}`",
            "- cache_ttl: `gateway-managed`",
            "- batch_supported: `verify_from_source`",
            f"- primary_entities: `api_endpoint:/v2/{endpoint}`",
            "- primary_actions: `INGEST_SOURCE`, `VALIDATE_API_SCOPE`",
            "- error_handling_notes: `Use governed gateway behavior and preserve evidence metadata.`",
            f"- source_pdf: `{record.path}`",
            f"- evidence_id: `{record.pdf_id.replace('pdf:', 'evidence:pdf:', 1)}`",
            "",
            "Processing note: this is an initial structured summary and intentionally avoids full-text PDF copying.",
            "",
        ]
    )


def _endpoint_slug(record: PdfSourceRecord) -> str:
    return record.pdf_id.removeprefix("pdf:api_endpoint:")


def _graph_layer_for_endpoint(endpoint: str) -> str:
    return "private_player_state" if endpoint.startswith("account") or endpoint == "characters" else "public_game_data"


def _scopes_for_endpoint(endpoint: str) -> str:
    if endpoint.startswith("account"):
        return "account"
    if endpoint == "characters":
        return "characters"
    return "none"


def _safe_source_label(record: PdfSourceRecord) -> str:
    if record.pdf_id == "pdf:api:key":
        return "the official API credential safety PDF"
    return record.file_name
