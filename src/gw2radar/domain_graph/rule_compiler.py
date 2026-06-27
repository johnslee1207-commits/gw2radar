import re
from dataclasses import dataclass

from gw2radar.domain_graph.domain_schema import DomainRule


@dataclass
class ConstraintRule:
    entity_type: str = ""
    property: str = ""
    operator: str = "eq"
    value: object = None
    relation_type: str = ""
    severity: str = "info"


_EXPR_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(.+)\.(.+) must be (.+)$"), "must_eq"),
    (re.compile(r"^(.+)\.(.+) must not be (.+)$"), "must_not_eq"),
    (re.compile(r"^(.+) requires (.+)$"), "requires_relation"),
]


class RuleCompiler:
    UNSUPPORTED = "unsupported"

    def compile(self, rule: DomainRule) -> ConstraintRule:
        for pattern, kind in _EXPR_PATTERNS:
            match = pattern.match(rule.rule.strip())
            if match:
                cr = self._build(rule, kind, match)
                cr.severity = rule.severity
                return cr
        return ConstraintRule(severity=rule.severity, operator=self.UNSUPPORTED,
                              entity_type=rule.rule)

    def _build(self, rule: DomainRule, kind: str, match: re.Match) -> ConstraintRule:
        if kind == "must_eq":
            return ConstraintRule(
                entity_type=match.group(1),
                property=match.group(2),
                operator="eq",
                value=match.group(3),
            )
        if kind == "must_not_eq":
            return ConstraintRule(
                entity_type=match.group(1),
                property=match.group(2),
                operator="neq",
                value=match.group(3),
            )
        if kind == "requires_relation":
            return ConstraintRule(
                entity_type=match.group(1),
                operator="requires_relation",
                relation_type=match.group(2),
            )
        return ConstraintRule(operator=self.UNSUPPORTED, entity_type=rule.rule)

    def compile_many(self, rules: list[DomainRule]) -> list[ConstraintRule]:
        return [self.compile(r) for r in rules]
