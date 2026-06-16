from gw2radar.ingest.evidence_writer import EvidenceWriter


def test_official_evidence_masks_authorization_and_tokens() -> None:
    raw_key = "12345678-abcdef-secret-key"

    evidence = EvidenceWriter().from_api_payload(
        evidence_id="evidence:official",
        endpoint="/v2/account",
        payload={
            "headers": {"authorization": f"Bearer {raw_key}"},
            "api_key": raw_key,
            "access_token": raw_key,
            "payload": {"name": "Test.1234"},
        },
    )

    assert raw_key not in str(evidence.raw_payload)
    assert evidence.raw_payload["api_key"] == "1234...-key"
    assert evidence.raw_payload["access_token"] == "1234...-key"
    assert evidence.raw_payload["headers"]["authorization"] == "Bear...-key"
