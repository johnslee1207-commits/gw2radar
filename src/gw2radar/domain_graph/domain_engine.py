import fnmatch
import os
from pathlib import Path

import yaml

import re as _re

from gw2radar.domain_graph.domain_schema import (
    BusinessEntityMapping,
    DomainEvent,
    DomainGraph,
    DomainRule,
    EdgeDef,
    NodeDef,
    NodeProperty,
    OOSKTypeRegistry,
    PropertyConstraint,
    SchemaDiff,
    StateMachine,
    StateTransition,
    TypeAlias,
)


def _parse_property(raw: str) -> NodeProperty:
    parts = raw.split("(")
    name = parts[0].strip()
    meta = parts[1].rstrip(")") if len(parts) > 1 else ""
    meta_parts = [m.strip() for m in meta.split(",")] if meta else []
    prop_type = "string"
    required = False
    enum_values: list[str] | None = None
    pc = PropertyConstraint()
    has_constraint = False
    for mp in meta_parts:
        if mp in ("required", "optional"):
            required = mp == "required"
        elif mp.startswith("enum:"):
            enum_str = mp.removeprefix("enum:")
            enum_values = [v.strip() for v in enum_str.split("/")]
            prop_type = "enum"
        elif mp in ("string", "int", "float", "bool"):
            prop_type = mp
        elif mp.startswith("min:"):
            pc.min_value = float(mp.removeprefix("min:"))
            has_constraint = True
        elif mp.startswith("max:"):
            pc.max_value = float(mp.removeprefix("max:"))
            has_constraint = True
        elif mp.startswith("pattern:"):
            pc.pattern = mp.removeprefix("pattern:")
            has_constraint = True
    return NodeProperty(
        name=name, prop_type=prop_type, required=required,
        enum_values=enum_values, constraints=pc if has_constraint else None,
    )


def _parse_state_machine(raw: dict | None) -> StateMachine | None:
    if not raw:
        return None
    transitions = [
        StateTransition(
            from_state=t["from"],
            to_state=t["to"],
            trigger=t.get("trigger", ""),
            guard=t.get("guard", ""),
        )
        for t in raw.get("transitions", [])
    ]
    return StateMachine(
        states=raw.get("states", []),
        transitions=transitions,
        invariants=raw.get("invariants", []),
        initial_state=raw.get("initial_state", ""),
    )


def _dict_to_nodes(raw: list[dict]) -> dict[str, NodeDef]:
    nodes: dict[str, NodeDef] = {}
    for item in raw:
        props = [_parse_property(p["name"]) for p in item.get("properties", [])]
        nd = NodeDef(
            type=item["type"],
            description=item.get("description", ""),
            properties=props,
            constraints=item.get("constraints", []),
            lifecycle=_parse_state_machine(item.get("lifecycle")),
        )
        nodes[nd.type] = nd
    return nodes


def _dict_to_edges(raw: list[dict]) -> dict[str, EdgeDef]:
    edges: dict[str, EdgeDef] = {}
    for item in raw:
        ed = EdgeDef(
            type=item["type"],
            description=item.get("description", ""),
            source_types=item.get("source", item.get("source_types", [])),
            target_types=item.get("target", item.get("target_types", [])),
            cardinality=item.get("cardinality", "N:N"),
        )
        edges[ed.type] = ed
    return edges


def _dict_to_events(raw: list[dict]) -> list[DomainEvent]:
    return [
        DomainEvent(
            name=ev["name"],
            description=ev.get("description", ""),
            source=ev.get("source", ""),
            triggers=ev.get("triggers", []),
            produces=ev.get("produces", []),
        )
        for ev in raw
    ]


def _dict_to_rules(raw: list[dict]) -> list[DomainRule]:
    return [
        DomainRule(
            name=r["name"],
            description=r.get("description", ""),
            rule=r.get("rule", ""),
            severity=r.get("severity", "info"),
        )
        for r in raw
    ]


class DomainGraphEngine:
    def load_file(self, filename: str) -> DomainGraph:
        path = Path(filename)
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return self._from_dict(raw)

    def load_all(self, pattern: str = "*domain.yaml") -> list[DomainGraph]:
        graphs: list[DomainGraph] = []
        for p in sorted(Path().glob(pattern)):
            graphs.append(self.load_file(str(p)))
        return graphs

    def _from_dict(self, raw: dict) -> DomainGraph:
        aliases = [
            TypeAlias(
                local_type=a["local_type"],
                equivalent_to=a["equivalent_to"],
                source_domain=a.get("source_domain", ""),
                confidence=a.get("confidence", 1.0),
            )
            for a in raw.get("type_aliases", [])
        ]
        return DomainGraph(
            domain=raw.get("domain", ""),
            version=raw.get("version", "1.0"),
            description=raw.get("description", ""),
            nodes=_dict_to_nodes(raw.get("nodes", [])),
            edges=_dict_to_edges(raw.get("edges", [])),
            events=_dict_to_events(raw.get("events", [])),
            rules=_dict_to_rules(raw.get("rules", [])),
            type_aliases=aliases,
        )

    def validate(self, dg: DomainGraph) -> list[str]:
        errors: list[str] = []
        known_nodes = set(dg.nodes.keys())

        for etype, ed in dg.edges.items():
            for st in ed.source_types:
                if st not in known_nodes:
                    errors.append(f"Edge '{etype}': source type '{st}' not found in nodes.")
            for tt in ed.target_types:
                if tt not in known_nodes:
                    errors.append(f"Edge '{etype}': target type '{tt}' not found in nodes.")

        for ev in dg.events:
            if ev.source and ev.source not in known_nodes:
                errors.append(f"Event '{ev.name}': source '{ev.source}' not found in nodes.")
            for prod in ev.produces:
                if prod not in known_nodes:
                    errors.append(f"Event '{ev.name}': produces '{prod}' not found in nodes.")

        for nt, nd in dg.nodes.items():
            if nd.lifecycle is not None:
                sm = nd.lifecycle
                state_set = set(sm.states)
                if sm.initial_state and sm.initial_state not in state_set:
                    errors.append(f"Node '{nt}': lifecycle initial_state '{sm.initial_state}' not in states list.")
                for i, t in enumerate(sm.transitions):
                    if t.from_state not in state_set:
                        errors.append(f"Node '{nt}': lifecycle transition[{i}] from_state '{t.from_state}' not in states.")
                    if t.to_state not in state_set:
                        errors.append(f"Node '{nt}': lifecycle transition[{i}] to_state '{t.to_state}' not in states.")
                all_transitional = set()
                for t in sm.transitions:
                    all_transitional.add(t.from_state)
                    all_transitional.add(t.to_state)
                orphaned = state_set - all_transitional
                if orphaned and sm.states:
                    errors.append(f"Node '{nt}': lifecycle states {sorted(orphaned)} have no transitions.")

        return errors

    def schema_diff(self, old: DomainGraph, new: DomainGraph) -> SchemaDiff:
        added_nodes = [n for n in new.nodes if n not in old.nodes]
        removed_nodes = [n for n in old.nodes if n not in new.nodes]
        added_edges = [e for e in new.edges if e not in old.edges]
        removed_edges = [e for e in old.edges if e not in new.edges]

        changed_properties: list[dict] = []
        breaking_changes: list[str] = list(removed_nodes)
        for ntype in added_nodes:
            breaking_changes.append(f"Added node type '{ntype}' (minor)")
        for etype in removed_edges:
            if etype in old.edges:
                breaking_changes.append(f"Removed edge '{etype}'")

        for ntype in new.nodes:
            old_node = old.nodes.get(ntype)
            if not old_node:
                continue
            old_prop_names = {p.name for p in old_node.properties}
            new_prop_names = {p.name for p in new.nodes[ntype].properties}
            removed_props = old_prop_names - new_prop_names
            if removed_props:
                breaking_changes.append(f"Node '{ntype}': removed properties {removed_props}")
                changed_properties.append({
                    "node": ntype, "removed": sorted(removed_props),
                })
            added_props = new_prop_names - old_prop_names
            if added_props:
                changed_properties.append({
                    "node": ntype, "added": sorted(added_props),
                })

        backward_compatible = len(breaking_changes) == 0
        return SchemaDiff(
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            changed_properties=changed_properties,
            backward_compatible=backward_compatible,
            breaking_changes=breaking_changes,
        )

    def compile_to_oosk(self, dg: DomainGraph) -> OOSKTypeRegistry:
        registry = OOSKTypeRegistry(
            domain_types=list(dg.nodes.keys()),
            relation_types=list(dg.edges.keys()),
        )
        for ev in dg.events:
            for prod in ev.produces:
                if prod not in registry.evidence_types:
                    registry.evidence_types.append(prod)
            action_entry = {
                "triggered_by": ev.name,
                "source": ev.source,
                "effects": ev.triggers,
                "produces": ev.produces,
            }
            registry.action_types[ev.name] = action_entry
        for rule in dg.rules:
            registry.constraint_rules.append({
                "name": rule.name,
                "severity": rule.severity,
                "rule": rule.rule,
            })
        return registry

    def compile_to_bors(self, dg: DomainGraph) -> list[BusinessEntityMapping]:
        return [
            BusinessEntityMapping(
                domain_type=ntype,
                bors_type=f"{ntype}Value",
                properties=[p.name for p in nd.properties],
            )
            for ntype, nd in dg.nodes.items()
        ]

    def resolve_aliases(self, dg: DomainGraph) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for alias in dg.type_aliases:
            mapping[alias.local_type] = alias.equivalent_to
        return mapping

    def merge(self, graphs: list[DomainGraph]) -> DomainGraph:
        if not graphs:
            return DomainGraph()
        merged = DomainGraph(
            domain="+".join(g.domain for g in graphs),
            version=".".join(g.version for g in graphs),
            description="Merged: " + "; ".join(g.description for g in graphs if g.description),
        )
        seen_nodes: set[str] = set()
        seen_edges: set[str] = set()
        seen_events: set[str] = set()
        seen_rules: set[str] = set()
        seen_aliases: set[str] = set()

        alias_map: dict[str, str] = {}
        for g in graphs:
            for alias in g.type_aliases:
                alias_map[alias.local_type] = alias.equivalent_to

        for g in graphs:
            for nname, nd in g.nodes.items():
                effective_name = alias_map.get(nname, nname)
                if effective_name not in seen_nodes:
                    merged.nodes[effective_name] = nd
                    seen_nodes.add(effective_name)
            for ename, ed in g.edges.items():
                if ename not in seen_edges:
                    merged.edges[ename] = ed
                    seen_edges.add(ename)
            for ev in g.events:
                if ev.name not in seen_events:
                    merged.events.append(ev)
                    seen_events.add(ev.name)
            for r in g.rules:
                if r.name not in seen_rules:
                    merged.rules.append(r)
                    seen_rules.add(r.name)
            for alias in g.type_aliases:
                key = f"{alias.local_type}->{alias.equivalent_to}"
                if key not in seen_aliases:
                    merged.type_aliases.append(alias)
                    seen_aliases.add(key)

        return merged

    def find_common_structure(self, graphs: list[DomainGraph]) -> dict:
        if not graphs:
            return {"common_nodes": [], "common_edges": [], "common_events": [], "common_rules": []}
        node_sets = [set(g.nodes.keys()) for g in graphs]
        edge_sets = [set(g.edges.keys()) for g in graphs]
        event_sets = [set(e.name for e in g.events) for g in graphs]
        rule_sets = [set(r.name for r in g.rules) for g in graphs]
        return {
            "common_nodes": sorted(set.intersection(*node_sets)),
            "common_edges": sorted(set.intersection(*edge_sets)),
            "common_events": sorted(set.intersection(*event_sets)),
            "common_rules": sorted(set.intersection(*rule_sets)),
        }
