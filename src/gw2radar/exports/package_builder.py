import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.reports.markdown_report import generate_markdown_report


GOAL_GAP_FIELDS = [
    "entity_id",
    "name",
    "entity_type",
    "required_quantity",
    "owned_quantity",
    "missing_quantity",
    "completed",
]

ACTION_FIELDS = [
    "id",
    "action_type",
    "title",
    "target_entity_id",
    "target_goal_id",
    "priority_score",
    "urgency",
    "reason_codes",
    "evidence_refs",
    "explanation",
]


@dataclass(frozen=True)
class ExportPackage:
    goal_id: str
    output_dir: Path
    files: list[Path]
    manifest_path: Path


def build_export_package(graph: GraphData, goal_id: str, output_root: Path) -> ExportPackage:
    goal_slug = _safe_slug(goal_id)
    output_dir = output_root / goal_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    gap = calculate_goal_gap(graph, goal_id)
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    report = generate_markdown_report(graph, goal_id)

    report_path = output_dir / "goal_report.md"
    gap_path = output_dir / "goal_gap.csv"
    actions_path = output_dir / "recommended_actions.csv"
    manifest_path = output_dir / "package_manifest.json"

    report_path.write_text(report, encoding="utf-8")
    _write_gap_csv(gap_path, gap)
    _write_actions_csv(actions_path, actions)

    files = [report_path, gap_path, actions_path, manifest_path]
    manifest = _build_manifest(goal_id, gap.goal_name, output_dir, files)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return ExportPackage(goal_id=goal_id, output_dir=output_dir, files=files, manifest_path=manifest_path)


def _write_gap_csv(path: Path, gap: Any) -> None:
    rows = gap.completed_requirements + gap.missing_requirements
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=GOAL_GAP_FIELDS)
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "entity_id": item.entity_id,
                    "name": item.name,
                    "entity_type": item.entity_type.value,
                    "required_quantity": f"{item.required_quantity:g}",
                    "owned_quantity": f"{item.owned_quantity:g}",
                    "missing_quantity": f"{item.missing_quantity:g}",
                    "completed": str(item.completed).lower(),
                }
            )


def _write_actions_csv(path: Path, actions: list[Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACTION_FIELDS)
        writer.writeheader()
        for action in actions:
            writer.writerow(
                {
                    "id": action.id,
                    "action_type": action.action_type.value,
                    "title": action.title,
                    "target_entity_id": action.target_entity_id or "",
                    "target_goal_id": action.target_goal_id or "",
                    "priority_score": f"{action.priority_score:.2f}",
                    "urgency": action.urgency,
                    "reason_codes": "|".join(action.reason_codes),
                    "evidence_refs": "|".join(action.evidence_refs),
                    "explanation": action.explanation,
                }
            )


def _build_manifest(goal_id: str, goal_name: str, output_dir: Path, files: list[Path]) -> dict[str, Any]:
    return {
        "schema_version": "gw2radar.export_package.v1",
        "generated_at": "deterministic-mvp",
        "goal_id": goal_id,
        "goal_name": goal_name,
        "package_type": "legendary_goal_report",
        "recommendation_boundary": "informational_manual_actions_only",
        "files": [
            {
                "name": path.name,
                "relative_path": path.relative_to(output_dir).as_posix(),
                "media_type": _media_type(path),
                "generated_at": datetime(2026, 6, 16, tzinfo=timezone.utc).isoformat(),
            }
            for path in files
        ],
    }


def _media_type(path: Path) -> str:
    if path.suffix == ".md":
        return "text/markdown"
    if path.suffix == ".csv":
        return "text/csv"
    if path.suffix == ".json":
        return "application/json"
    return "application/octet-stream"


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()
