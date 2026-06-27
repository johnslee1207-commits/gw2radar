from pathlib import Path

from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.domain_graph.domain_schema import (
    DomainRule,
    EdgeDef,
    NodeDef,
    NodeProperty,
)
from gw2radar.domain_graph.rule_compiler import RuleCompiler


def test_engine_loads_yaml() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    assert dg.domain == "GW2Radar"
    assert len(dg.nodes) >= 10
    assert "Account" in dg.nodes
    assert "Goal" in dg.nodes
    assert len(dg.edges) >= 10
    assert len(dg.rules) >= 3


def test_validate_passes() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    errors = engine.validate(dg)
    assert errors == [], f"Validation errors: {errors}"


def test_validate_detects_missing_node() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    dg.edges["bad_edge"] = EdgeDef(
        type="bad_edge",
        source_types=["NonExistentType"],
        target_types=["AlsoMissing"],
    )
    errors = engine.validate(dg)
    assert len(errors) == 2
    assert all("not found" in e for e in errors)


def test_compile_to_oosk() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    registry = engine.compile_to_oosk(dg)
    assert "Account" in registry.domain_types
    assert "Goal" in registry.domain_types
    assert len(registry.relation_types) >= 10
    assert len(registry.constraint_rules) >= 3


def test_compile_to_bors() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    mappings = engine.compile_to_bors(dg)
    assert len(mappings) >= 10
    assert any(m.domain_type == "Account" for m in mappings)
    assert all(m.bors_type.endswith("Value") for m in mappings)


def test_merge_deduplicates() -> None:
    engine = DomainGraphEngine()
    dg1 = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    dg2 = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    merged = engine.merge([dg1, dg2])
    total_nodes = len(dg1.nodes) + len(dg2.nodes)
    assert len(merged.nodes) <= total_nodes
    assert "Account" in merged.nodes
    assert merged.domain == "GW2Radar+GW2Radar"


def test_find_common_structure() -> None:
    engine = DomainGraphEngine()
    dg1 = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    dg2 = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    common = engine.find_common_structure([dg1, dg2])
    assert "common_nodes" in common
    assert isinstance(common["common_nodes"], list)


def test_rule_compiler_must_eq() -> None:
    compiler = RuleCompiler()
    rule = DomainRule(name="test", rule="ExecutionRun.seed must be non-zero")
    cr = compiler.compile(rule)
    assert cr.entity_type == "ExecutionRun"
    assert cr.property == "seed"
    assert cr.operator == "eq"
    assert cr.value == "non-zero"


def test_rule_compiler_must_not_eq() -> None:
    compiler = RuleCompiler()
    rule = DomainRule(name="test", rule="Account.status must not be closed")
    cr = compiler.compile(rule)
    assert cr.operator == "neq"
    assert cr.entity_type == "Account"


def test_rule_compiler_requires_relation() -> None:
    compiler = RuleCompiler()
    rule = DomainRule(name="test", rule="Report requires Evidence")
    cr = compiler.compile(rule)
    assert cr.operator == "requires_relation"
    assert cr.entity_type == "Report"
    assert cr.relation_type == "Evidence"


def test_rule_compiler_unsupported() -> None:
    compiler = RuleCompiler()
    rule = DomainRule(name="test", rule="something completely different")
    cr = compiler.compile(rule)
    assert cr.operator == "unsupported"


def test_domain_loads() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    assert dg.domain == "GW2Radar"
    errors = engine.validate(dg)
    assert errors == [], f"Domain validation errors: {errors}"
