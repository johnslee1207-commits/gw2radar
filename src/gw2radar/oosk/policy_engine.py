from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PolicyDef:
    name: str
    severity: str = "info"
    check_fn: Callable[..., bool] | None = None
    enabled: bool = True
    description: str = ""


@dataclass
class PolicyResult:
    name: str
    passed: bool
    severity: str = "info"
    message: str = ""


class PolicyEngine:
    def __init__(self) -> None:
        self._policies: dict[str, PolicyDef] = {}

    def add(self, policy: PolicyDef) -> None:
        self._policies[policy.name] = policy

    def remove(self, name: str) -> None:
        self._policies.pop(name, None)

    def disable(self, name: str) -> None:
        if name in self._policies:
            self._policies[name].enabled = False

    def enable(self, name: str) -> None:
        if name in self._policies:
            self._policies[name].enabled = True

    def evaluate(self, context: dict[str, Any]) -> list[PolicyResult]:
        results: list[PolicyResult] = []
        for pdef in self._policies.values():
            if not pdef.enabled:
                continue
            if pdef.check_fn:
                try:
                    passed = pdef.check_fn(context)
                except Exception:
                    passed = False
                results.append(PolicyResult(
                    name=pdef.name,
                    passed=passed,
                    severity=pdef.severity,
                    message=f"Policy '{pdef.name}': {'pass' if passed else 'fail'}",
                ))
        return results
