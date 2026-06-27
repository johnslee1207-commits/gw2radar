"""Three-layer ontology CLI: DGSK → OOSK → BORS pipeline."""

import argparse
import json
import sys
from pathlib import Path

from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.oosk.constraint_engine import ConstraintEngine
from gw2radar.oosk.runtime_mapper import RuntimeMapper
from gw2radar.oosk.runtime_store import RuntimeStore
from gw2radar.pipeline import ThreeLayerPipeline


def cmd_validate(args: argparse.Namespace) -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(args.file)
    errors = engine.validate(dg)
    if errors:
        print(f"VALIDATION FAILED ({len(errors)} errors):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Domain '{dg.domain}' v{dg.version}: VALID")
    print(f"  Nodes: {len(dg.nodes)}, Edges: {len(dg.edges)}")
    print(f"  Events: {len(dg.events)}, Rules: {len(dg.rules)}")


def cmd_info(args: argparse.Namespace) -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(args.file)
    print(json.dumps({
        "domain": dg.domain,
        "version": dg.version,
        "description": dg.description,
        "node_count": len(dg.nodes),
        "nodes": list(dg.nodes.keys()),
        "edge_count": len(dg.edges),
        "edges": list(dg.edges.keys()),
        "event_count": len(dg.events),
        "events": [e.name for e in dg.events],
        "rule_count": len(dg.rules),
        "rules": [r.name for r in dg.rules],
        "type_aliases": [(a.local_type, a.equivalent_to) for a in dg.type_aliases],
    }, indent=2))


def cmd_diff(args: argparse.Namespace) -> None:
    engine = DomainGraphEngine()
    old = engine.load_file(args.old)
    new = engine.load_file(args.new)
    diff = engine.schema_diff(old, new)
    print(json.dumps({
        "backward_compatible": diff.backward_compatible,
        "breaking_changes": diff.breaking_changes,
        "added_nodes": diff.added_nodes,
        "removed_nodes": diff.removed_nodes,
        "added_edges": diff.added_edges,
        "removed_edges": diff.removed_edges,
        "changed_properties": diff.changed_properties,
    }, indent=2))


def cmd_pipeline(args: argparse.Namespace) -> None:
    runtime: dict = {}
    if args.qa_passed is not None:
        runtime["qa_gate"] = {"passed": args.qa_passed, "total": args.qa_total or args.qa_passed}
    if args.evidence_chain is not None:
        runtime["evidence"] = {"chain_intact": args.evidence_chain}
    if args.action_total is not None:
        runtime["action_history"] = {
            "total": args.action_total,
            "failed": args.action_failed or 0,
        }

    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(args.file, runtime_state=runtime if runtime else None)
    print(json.dumps(result, indent=2, default=str))


def cmd_compile(args: argparse.Namespace) -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(args.file)
    if args.target == "oosk":
        registry = engine.compile_to_oosk(dg)
        print(json.dumps({
            "domain_types": registry.domain_types,
            "relation_types": registry.relation_types,
            "action_types": {k: v for k, v in registry.action_types.items()},
            "constraint_rules": registry.constraint_rules,
        }, indent=2))
    elif args.target == "bors":
        mappings = engine.compile_to_bors(dg)
        print(json.dumps([
            {"domain_type": m.domain_type, "bors_type": m.bors_type, "properties": m.properties}
            for m in mappings
        ], indent=2))


def cmd_plan(args: argparse.Namespace) -> None:
    from gw2radar.oosk.planner import Orchestrator, Planner
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan(args.intent, store)
    orchestrator = Orchestrator(planner)
    print(json.dumps({
        "plan_id": plan.plan_id,
        "intent": plan.intent,
        "steps": [
            {"action_id": s.action_id, "description": s.description,
             "depends_on": s.depends_on, "estimated_cost": s.estimated_cost}
            for s in plan.steps
        ],
        "total_estimated_cost": plan.total_estimated_cost,
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Three-layer ontology CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate a domain YAML")
    p_validate.add_argument("file", type=str)

    p_info = sub.add_parser("info", help="Show domain info")
    p_info.add_argument("file", type=str)

    p_diff = sub.add_parser("diff", help="Diff two domain versions")
    p_diff.add_argument("old", type=str)
    p_diff.add_argument("new", type=str)

    p_pipeline = sub.add_parser("pipeline", help="Run full DGSK→OOSK→BORS pipeline")
    p_pipeline.add_argument("file", type=str)
    p_pipeline.add_argument("--qa-passed", type=int, default=None)
    p_pipeline.add_argument("--qa-total", type=int, default=None)
    p_pipeline.add_argument("--evidence-chain", type=bool, default=None)
    p_pipeline.add_argument("--action-total", type=int, default=None)
    p_pipeline.add_argument("--action-failed", type=int, default=None)

    p_compile = sub.add_parser("compile", help="Compile domain to OOSK or BORS")
    p_compile.add_argument("file", type=str)
    p_compile.add_argument("--target", choices=["oosk", "bors"], default="oosk")

    p_plan = sub.add_parser("plan", help="Create execution plan from intent")
    p_plan.add_argument("intent", type=str)

    args = parser.parse_args()
    handlers = {
        "validate": cmd_validate,
        "info": cmd_info,
        "diff": cmd_diff,
        "pipeline": cmd_pipeline,
        "compile": cmd_compile,
        "plan": cmd_plan,
    }
    handler = handlers.get(args.command)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()
