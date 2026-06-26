from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.guild_readiness import (
    GuildCreateRequest,
    TeamCreateRequest,
    TeamMemberInviteRequest,
    compute_team_readiness,
    create_guild,
    create_team,
    invite_team_member,
    render_guild_readiness_report,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.mappers.guild_mapper import compute_member_readiness_from_graph, enrich_guild_entities


def test_guild_mapper_enriches_entities() -> None:
    graph = build_mock_graph()
    count_before = len(graph.entities)
    enrich_guild_entities(graph)
    assert len(graph.entities) >= count_before
    for eid, entity in graph.entities.items():
        if "quantity" in entity.properties:
            assert entity.freshness_status is not None


def test_compute_readiness_from_graph() -> None:
    graph = build_mock_graph()
    score = compute_member_readiness_from_graph("mock:account:lee", graph)
    assert score > 0


def test_compute_readiness_unknown_account() -> None:
    graph = build_mock_graph()
    score = compute_member_readiness_from_graph("nonexistent", graph)
    assert score == 0.0


def test_guild_readiness_with_graph(tmp_path: Path) -> None:
    temp_dir = Path(".test_tmp") / f"guild-onto-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'test.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            guild = create_guild(session, GuildCreateRequest(name="Test Guild"))
            team = create_team(session, TeamCreateRequest(guild_id=guild.guild_id, name="Strike Team"))
            invite_team_member(
                session, team.team_id,
                TeamMemberInviteRequest(user_id="mock:account:lee", display_name="Lee", preferred_roles=["dps", "healer"]),
            )
            result = compute_team_readiness(session, team.team_id, graph=graph)
            assert result.readiness_score >= 0
            assert len(result.role_coverage) > 0
            assert any(c.role == "dps" for c in result.role_coverage)
    finally:
        close_database()


def test_guild_report_includes_heatmap() -> None:
    temp_dir = Path(".test_tmp") / f"guild-heatmap-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'test.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            guild = create_guild(session, GuildCreateRequest(name="Heatmap Guild"))
            team = create_team(session, TeamCreateRequest(guild_id=guild.guild_id, name="Raid Team"))
            invite_team_member(session, team.team_id, TeamMemberInviteRequest(user_id="u1", display_name="Player1", preferred_roles=["quickness"]))
            invite_team_member(session, team.team_id, TeamMemberInviteRequest(user_id="u2", display_name="Player2", preferred_roles=["alacrity"]))
            result = compute_team_readiness(session, team.team_id)
        report = render_guild_readiness_report(result)
        assert "Role Coverage Heatmap" in report
        assert "quickness" in report.lower()
        assert "alacrity" in report.lower()
    finally:
        close_database()
