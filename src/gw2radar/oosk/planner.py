from dataclasses import dataclass, field
from typing import Any, Callable

from gw2radar.graph.graph_query import GraphData
from gw2radar.oosk.runtime_store import RuntimeStore


@dataclass
class PlanStep:
    action_id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    estimated_cost: float = 1.0
    handler: Callable[..., dict] | None = None


@dataclass
class Plan:
    plan_id: str
    intent: str
    steps: list[PlanStep] = field(default_factory=list)
    total_estimated_cost: float = 0.0


@dataclass
class ExecutionResult:
    step_results: list[dict] = field(default_factory=list)
    success: bool = True
    failed_step: str | None = None


class Planner:
    def create_plan(self, intent: str, store: RuntimeStore) -> Plan:
        intent_lower = intent.lower()
        steps: list[PlanStep] = []

        if "publish" in intent_lower:
            steps = self._publish_plan(store)
        elif "sync" in intent_lower:
            steps = self._sync_plan(store)
        elif "review" in intent_lower:
            steps = self._review_plan(store)
        else:
            steps = [PlanStep(
                action_id="generic_analyze",
                description=f"Analyze for intent: {intent}",
                preconditions=["graph_has_entities"],
            )]

        total_cost = sum(s.estimated_cost for s in steps)
        return Plan(plan_id=f"plan:{intent}", intent=intent,
                    steps=steps, total_estimated_cost=total_cost)

    def _publish_plan(self, store: RuntimeStore) -> list[PlanStep]:
        return [
            PlanStep("validate_evidence", "Validate evidence chain integrity",
                     estimated_cost=2.0, preconditions=["evidence_exists"]),
            PlanStep("run_qa", "Run QA gate",
                     depends_on=["validate_evidence"],
                     estimated_cost=3.0, preconditions=["evidence_valid"]),
            PlanStep("check_compliance", "Check compliance rules",
                     depends_on=["run_qa"],
                     estimated_cost=1.5, preconditions=["qa_passed"]),
            PlanStep("generate_report", "Generate final report",
                     depends_on=["check_compliance"],
                     estimated_cost=5.0, preconditions=["compliance_ok"]),
            PlanStep("publish", "Publish report",
                     depends_on=["generate_report"],
                     estimated_cost=1.0, preconditions=["report_ready"]),
        ]

    def _sync_plan(self, store: RuntimeStore) -> list[PlanStep]:
        return [
            PlanStep("authenticate", "Authenticate with remote source",
                     estimated_cost=1.0),
            PlanStep("fetch_data", "Fetch remote data",
                     depends_on=["authenticate"],
                     estimated_cost=5.0),
            PlanStep("validate_data", "Validate fetched data",
                     depends_on=["fetch_data"],
                     estimated_cost=2.0),
            PlanStep("merge_state", "Merge into runtime state",
                     depends_on=["validate_data"],
                     estimated_cost=3.0),
        ]

    def _review_plan(self, store: RuntimeStore) -> list[PlanStep]:
        return [
            PlanStep("collect_sources", "Collect all review sources",
                     estimated_cost=2.0),
            PlanStep("run_constraints", "Evaluate all constraints",
                     depends_on=["collect_sources"],
                     estimated_cost=3.0),
            PlanStep("generate_review", "Generate review summary",
                     depends_on=["run_constraints"],
                     estimated_cost=2.0),
        ]


class Orchestrator:
    def __init__(self, planner: Planner) -> None:
        self._planner = planner

    def execute(self, plan: Plan, store: RuntimeStore,
                action_registry: dict[str, Callable[..., dict]] | None = None) -> ExecutionResult:
        registry = action_registry or {}
        executed: set[str] = set()
        results: list[dict] = []

        def _step_ready(step: PlanStep) -> bool:
            return all(dep in executed for dep in step.depends_on)

        remaining = list(plan.steps)
        max_iterations = len(plan.steps) * 3
        iterations = 0

        while remaining and iterations < max_iterations:
            iterations += 1
            batch = [s for s in remaining if _step_ready(s)]
            if not batch:
                return ExecutionResult(
                    step_results=results, success=False,
                    failed_step=remaining[0].action_id if remaining else None,
                )
            for step in batch:
                remaining.remove(step)
                handler = registry.get(step.action_id, self._default_handler)
                try:
                    result = handler(step=step, store=store)
                    results.append({"step": step.action_id, "status": "done", "output": result})
                    executed.add(step.action_id)
                except Exception as exc:
                    return ExecutionResult(
                        step_results=results, success=False,
                        failed_step=step.action_id,
                    )

        return ExecutionResult(step_results=results, success=len(remaining) == 0)

    def _default_handler(self, **kwargs: Any) -> dict:
        return {"status": "simulated", "step": getattr(kwargs.get("step"), "action_id", "unknown")}
