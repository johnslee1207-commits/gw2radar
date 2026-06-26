from pathlib import Path
from uuid import uuid4

from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.action_registry import (
    ActionPreconditionError,
    generate_do_not_sell,
    generate_legendary_plan,
    list_registry,
    reserve_material_for_goal,
)


def test_list_registry_contains_expected_actions() -> None:
    registry = list_registry()
    assert "reserve_material_for_goal" in registry
    assert "generate_do_not_sell" in registry
    assert "generate_legendary_plan" in registry


def test_registry_entry_has_governance_fields() -> None:
    entry = list_registry()["reserve_material_for_goal"]
    assert len(entry.preconditions) > 0
    assert len(entry.effects) > 0
    assert len(entry.qa_hooks) > 0
    assert entry.privacy_policy == "private_summary_only"


def test_reserve_material_fails_without_snapshot() -> None:
    graph = build_mock_graph()
    try:
        reserve_material_for_goal(
            graph,
            None,
            item_id="gw2:item:nonexistent",
            goal_id="gw2:goal:aurora",
            quantity=10,
        )
        assert False, "Expected ActionPreconditionError"
    except ActionPreconditionError:
        pass


def test_generate_legendary_plan_with_session(tmp_path: Path) -> None:
    temp_dir = Path(".test_tmp") / f"action-reg-legendary-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'test.db'}")
        init_db()
        graph = build_mock_graph()
        from gw2radar.db import session as db_session
        with db_session.SessionLocal() as session:
            result = generate_legendary_plan(graph, session, "gw2:goal:aurora")
            assert result.description.startswith("Generated legendary plan")
            assert "gw2:goal:aurora" in result.affected_entity_ids
    finally:
        close_database()


def test_generate_do_not_sell_with_session(tmp_path: Path) -> None:
    temp_dir = Path(".test_tmp") / f"action-reg-dns-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'test.db'}")
        init_db()
        graph = build_mock_graph()
        from gw2radar.db import session as db_session
        with db_session.SessionLocal() as session:
            generate_legendary_plan(graph, session, "gw2:goal:aurora")
            result = generate_do_not_sell(graph, session, "gw2:goal:aurora")
            assert result.description.startswith("Generated do-not-sell list")
    finally:
        close_database()
