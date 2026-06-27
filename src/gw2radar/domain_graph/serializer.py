"""Serialize DomainGraph to/from YAML."""

from pathlib import Path
from typing import Any

import yaml

from gw2radar.domain_graph.domain_schema import (
    DomainGraph,
    DomainRule,
    EdgeDef,
    NodeDef,
    NodeProperty,
    TypeAlias,
)


def domain_graph_to_dict(dg: DomainGraph) -> dict[str, Any]:
    nodes_raw = []
    for ntype, nd in dg.nodes.items():
        item: dict[str, Any] = {"type": ntype}
        if nd.description:
            item["description"] = nd.description
        props_raw = []
        for p in nd.properties:
            parts = [p.name]
            meta_parts = []
            if p.required:
                meta_parts.append("required")
            if p.prop_type and p.prop_type != "string":
                if p.prop_type == "enum" and p.enum_values:
                    meta_parts.append(f"enum:{'/'.join(p.enum_values)}")
                else:
                    meta_parts.append(p.prop_type)
            if p.constraints:
                if p.constraints.min_value is not None:
                    meta_parts.append(f"min:{p.constraints.min_value}")
                if p.constraints.max_value is not None:
                    meta_parts.append(f"max:{p.constraints.max_value}")
                if p.constraints.pattern:
                    meta_parts.append(f"pattern:{p.constraints.pattern}")
            if meta_parts:
                parts.append(f"({' , '.join(meta_parts)})")
            props_raw.append({"name": "".join(parts)})
        if props_raw:
            item["properties"] = props_raw
        if nd.constraints:
            item["constraints"] = nd.constraints
        if nd.lifecycle:
            lf: dict[str, Any] = {}
            if nd.lifecycle.states:
                lf["states"] = nd.lifecycle.states
            if nd.lifecycle.initial_state:
                lf["initial_state"] = nd.lifecycle.initial_state
            if nd.lifecycle.transitions:
                lf["transitions"] = [
                    {"from": t.from_state, "to": t.to_state, "trigger": t.trigger}
                    for t in nd.lifecycle.transitions
                ]
            if nd.lifecycle.invariants:
                lf["invariants"] = nd.lifecycle.invariants
            if lf:
                item["lifecycle"] = lf
        nodes_raw.append(item)

    edges_raw = []
    for etype, ed in dg.edges.items():
        edge_item: dict[str, Any] = {
            "type": etype,
            "source": ed.source_types,
            "target": ed.target_types,
            "cardinality": ed.cardinality,
        }
        if ed.description:
            edge_item["description"] = ed.description
        edges_raw.append(edge_item)

    events_raw = []
    for ev in dg.events:
        ev_item: dict[str, Any] = {"name": ev.name}
        if ev.description:
            ev_item["description"] = ev.description
        if ev.source:
            ev_item["source"] = ev.source
        if ev.triggers:
            ev_item["triggers"] = ev.triggers
        if ev.produces:
            ev_item["produces"] = ev.produces
        events_raw.append(ev_item)

    rules_raw = []
    for rule in dg.rules:
        r_item: dict[str, Any] = {
            "name": rule.name,
            "rule": rule.rule,
            "severity": rule.severity,
        }
        if rule.description:
            r_item["description"] = rule.description
        rules_raw.append(r_item)

    result: dict[str, Any] = {
        "domain": dg.domain,
        "version": dg.version,
    }
    if dg.description:
        result["description"] = dg.description
    result["nodes"] = nodes_raw
    result["edges"] = edges_raw
    if events_raw:
        result["events"] = events_raw
    if rules_raw:
        result["rules"] = rules_raw
    if dg.type_aliases:
        result["type_aliases"] = [
            {"local_type": a.local_type, "equivalent_to": a.equivalent_to,
             "source_domain": a.source_domain, "confidence": a.confidence}
            for a in dg.type_aliases
        ]
    return result


def serialize(dg: DomainGraph, path: str | Path) -> None:
    data = domain_graph_to_dict(dg)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
