from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import (
    build_transition_plan,
    enrich_transition_plan_with_value_snapshot,
    import_build,
    match_account_gear,
    render_build_fit_report,
    evaluate_build_fit,
)
from gw2radar.commercial.account_value import build_account_value_snapshot
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import partial_account_gear, sample_build_import


def test_gear_transition_cost_sums_missing_requirements() -> None:
    temp_dir = Path(".test_tmp") / f"build-transition-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        matches = match_account_gear(build, partial_account_gear())
        plan = build_transition_plan(build, matches)

        assert plan.estimated_cost_gold == 30
        assert len(plan.missing_requirements) == 2
        assert all("Manually review" in step for step in plan.manual_steps)
    finally:
        close_database()


def test_value_snapshot_enriches_transition_plan_context() -> None:
    temp_dir = Path(".test_tmp") / f"build-transition-value-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())
            matches = match_account_gear(build, partial_account_gear())
            plan = build_transition_plan(build, matches)
            snapshot = build_account_value_snapshot(graph, session, top_limit=100)

        enriched = enrich_transition_plan_with_value_snapshot(plan, snapshot)
        result = evaluate_build_fit(build, partial_account_gear(), value_snapshot=snapshot)
        report = render_build_fit_report(result)

        assert enriched.value_context
        assert enriched.reserved_goal_notes
        assert "Account Value Context" in report
        assert "avoid using it as gear-conversion budget" in report
    finally:
        close_database()
