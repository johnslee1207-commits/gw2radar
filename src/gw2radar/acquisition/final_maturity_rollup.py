from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.maturity import build_acquisition_maturity_report
from gw2radar.acquisition.promotion_release_manifest import build_acquisition_promotion_release_manifest
from gw2radar.kb.kb_semantic_maturity import build_kb_semantic_maturity_report


class FinalMaturityComponent(BaseModel):
    component_id: str
    name: str
    score: float = Field(ge=0.0, le=1.0)
    status: str
    evidence_refs: list[str] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)


class FinalMaturityRollup(BaseModel):
    schema_version: str = "gw2radar.final_maturity_rollup.v1"
    overall_score: float = Field(ge=0.0, le=1.0)
    maturity_label: str
    release_ready: bool
    component_count: int
    components: list[FinalMaturityComponent]
    remaining_priorities: list[str] = Field(default_factory=list)
    evidence_chain: list[str] = Field(default_factory=list)
    safety_boundary: list[str] = Field(default_factory=list)


def build_final_maturity_rollup(session: Session) -> FinalMaturityRollup:
    kb = build_kb_semantic_maturity_report()
    acquisition = build_acquisition_maturity_report(session)
    manifest = build_acquisition_promotion_release_manifest(session)
    components = [
        FinalMaturityComponent(
            component_id="kb_semantic_spine",
            name="KB semantic graph and rule governance",
            score=kb.overall_score,
            status=kb.maturity_label,
            evidence_refs=["/api/v1/kb/semantic-maturity", "/api/v1/kb/release-readiness"],
            remaining_gaps=[priority.title for priority in kb.recommended_priorities[:3]],
        ),
        FinalMaturityComponent(
            component_id="acquisition_maturity",
            name="Acquisition source, policy, job, and evidence maturity",
            score=acquisition.overall_score,
            status=acquisition.maturity_label,
            evidence_refs=["/api/v1/acquisition/maturity", "/api/v1/acquisition/evidence-coverage"],
            remaining_gaps=acquisition.next_priorities,
        ),
        FinalMaturityComponent(
            component_id="promotion_release_manifest",
            name="Promotion workflow and release manifest",
            score=_manifest_score(manifest),
            status="ready" if manifest.release_ready else "blocked",
            evidence_refs=[
                "/api/v1/acquisition/promotion-workflow",
                "/api/v1/acquisition/promotion-action-plans",
                "/api/v1/acquisition/promotion-release-manifest",
            ],
            remaining_gaps=manifest.operator_steps,
        ),
    ]
    overall = round(sum(component.score for component in components) / len(components), 3)
    return FinalMaturityRollup(
        overall_score=overall,
        maturity_label=_label(overall),
        release_ready=all(component.status not in {"early", "blocked"} for component in components),
        component_count=len(components),
        components=components,
        remaining_priorities=_priorities(components),
        evidence_chain=[
            "/api/v1/kb/semantic-maturity",
            "/api/v1/kb/release-readiness",
            "/api/v1/acquisition/maturity",
            "/api/v1/acquisition/evidence-coverage",
            "/api/v1/acquisition/promotion-release-manifest",
        ],
        safety_boundary=[
            "Rollup is read-only and does not mutate KB, acquisition, rules, reports, or private data.",
            "Remaining priorities must be resolved by explicit operator actions and reviewed gates.",
            "No generated recommendation may invent facts, copy full source text, or promise market outcomes.",
        ],
    )


def render_final_maturity_rollup_markdown(rollup: FinalMaturityRollup) -> str:
    lines = [
        "# Final MVP Maturity Rollup",
        "",
        f"- schema_version: `{rollup.schema_version}`",
        f"- overall_score: `{rollup.overall_score:.3f}`",
        f"- maturity_label: `{rollup.maturity_label}`",
        f"- release_ready: `{str(rollup.release_ready).lower()}`",
        f"- component_count: `{rollup.component_count}`",
        "",
        "## Components",
        "",
        "| Component | Score | Status | Evidence | Remaining Gaps |",
        "|---|---:|---|---|---|",
    ]
    for component in rollup.components:
        lines.append(
            f"| {component.name} | {component.score:.3f} | {component.status} | "
            f"{_join(component.evidence_refs)} | {_join(component.remaining_gaps)} |"
        )
    lines.extend(["", "## Remaining Priorities", ""])
    lines.extend(f"- {item}" for item in rollup.remaining_priorities) if rollup.remaining_priorities else lines.append(
        "- none"
    )
    lines.extend(["", "## Evidence Chain", ""])
    lines.extend(f"- {item}" for item in rollup.evidence_chain)
    lines.extend(["", "## Safety Boundary", ""])
    lines.extend(f"- {item}" for item in rollup.safety_boundary)
    return "\n".join(lines) + "\n"


def _manifest_score(manifest) -> float:
    if manifest.release_ready:
        return 1.0
    penalty = min((manifest.blocker_count * 0.2) + (manifest.warning_count * 0.05), 0.7)
    return round(max(0.3, 0.85 - penalty), 3)


def _label(score: float) -> str:
    if score >= 0.9:
        return "release_ready"
    if score >= 0.75:
        return "mature_with_operator_gaps"
    if score >= 0.55:
        return "partial"
    return "early"


def _priorities(components: list[FinalMaturityComponent]) -> list[str]:
    priorities: list[str] = []
    for component in sorted(components, key=lambda item: item.score):
        priorities.extend(component.remaining_gaps)
    deduped: list[str] = []
    for item in priorities:
        if item and item not in deduped:
            deduped.append(item)
    return deduped[:8]


def _join(items: list[str]) -> str:
    return "; ".join(items) if items else "none"
