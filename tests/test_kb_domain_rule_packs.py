from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_domain_rule_packs import (
    DomainRulePackId,
    get_domain_rule_pack,
    import_domain_rule_pack,
    list_domain_rule_packs,
)
from gw2radar.kb.kb_models import KnowledgeReviewStatus
from gw2radar.kb.kb_repository import list_rules


def test_domain_rule_packs_are_reviewed_disabled_and_evidence_backed() -> None:
    packs = list_domain_rule_packs()
    rules = [rule for pack in packs for rule in pack.rules]

    assert {pack.pack_id for pack in packs} == set(DomainRulePackId)
    assert len(rules) >= 10
    assert all(rule.review_status == KnowledgeReviewStatus.REVIEWED for rule in rules)
    assert all(rule.enabled is False for rule in rules)
    assert all(rule.evidence_refs for rule in rules)
    assert all("guaranteed profit" not in rule.recommendation.lower() for rule in rules)
    assert any(pack.pack_id == DomainRulePackId.GUILD_PRIVACY_READINESS for pack in packs)
    assert any(pack.pack_id == DomainRulePackId.CREATOR_SIGNAL_SAFETY for pack in packs)


def test_domain_rule_pack_import_requires_confirmation_and_is_idempotent() -> None:
    temp_dir = Path(".test_tmp") / f"kb-domain-rule-pack-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            with pytest.raises(ValueError, match="requires confirmation"):
                import_domain_rule_pack(session, DomainRulePackId.MARKET_RETENTION, confirmed=False)

            first = import_domain_rule_pack(session, DomainRulePackId.MARKET_RETENTION, confirmed=True)
            second = import_domain_rule_pack(session, DomainRulePackId.MARKET_RETENTION, confirmed=True)
            rules = list_rules(session)

        assert first.created_count == len(get_domain_rule_pack(DomainRulePackId.MARKET_RETENTION).rules)
        assert second.created_count == 0
        assert second.skipped_existing_count == first.created_count
        assert all(rule.enabled is False for rule in rules)
    finally:
        close_database()


def test_domain_rule_pack_api_preview_and_import() -> None:
    temp_dir = Path(".test_tmp") / f"kb-domain-rule-pack-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        listed = client.get("/api/v1/kb/rule-packs")
        preview = client.get("/api/v1/kb/rule-packs/returner_recovery")
        blocked = client.post("/api/v1/kb/rule-packs/returner_recovery/import", json={"confirmed": False})
        imported = client.post("/api/v1/kb/rule-packs/returner_recovery/import", json={"confirmed": True})

        assert listed.status_code == 200
        assert listed.json()["data"]["count"] == 5
        assert preview.status_code == 200
        assert preview.json()["data"]["pack"]["pack_id"] == "returner_recovery"
        assert blocked.status_code == 400
        assert imported.status_code == 200
        assert imported.json()["data"]["result"]["created_count"] == 2
        assert all(rule["enabled"] is False for rule in imported.json()["data"]["result"]["rules"])
    finally:
        close_database()
