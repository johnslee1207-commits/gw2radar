import csv
import json
import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.exports.package_builder import ACTION_FIELDS, GOAL_GAP_FIELDS, build_export_package
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions


def test_export_package_contains_expected_files_and_manifest() -> None:
    temp_dir = Path(".test_tmp") / f"export-{uuid4().hex}"
    try:
        graph = build_mock_graph()
        generate_actions(graph, "gw2:goal:aurora")

        package = build_export_package(graph, "gw2:goal:aurora", temp_dir)

        expected = {
            "goal_report.md",
            "goal_gap.csv",
            "recommended_actions.csv",
            "package_manifest.json",
        }
        assert {path.name for path in package.files} == expected
        assert all(path.exists() for path in package.files)

        manifest = json.loads(package.manifest_path.read_text(encoding="utf-8"))
        assert manifest["schema_version"] == "gw2radar.export_package.v1"
        assert manifest["recommendation_boundary"] == "informational_manual_actions_only"
        assert {file["name"] for file in manifest["files"]} == expected
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_package_csv_headers_are_stable() -> None:
    temp_dir = Path(".test_tmp") / f"export-{uuid4().hex}"
    try:
        graph = build_mock_graph()
        package = build_export_package(graph, "gw2:goal:aurora", temp_dir)
        output_dir = package.output_dir

        with (output_dir / "goal_gap.csv").open("r", encoding="utf-8", newline="") as handle:
            gap_reader = csv.DictReader(handle)
            assert gap_reader.fieldnames == GOAL_GAP_FIELDS
            gap_rows = list(gap_reader)

        with (output_dir / "recommended_actions.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            action_reader = csv.DictReader(handle)
            assert action_reader.fieldnames == ACTION_FIELDS
            action_rows = list(action_reader)

        assert any(row["entity_id"] == "gw2:item:mystic_clover" for row in gap_rows)
        assert any(row["action_type"] == "do_daily" for row in action_rows)
        assert all(row["explanation"] for row in action_rows)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
