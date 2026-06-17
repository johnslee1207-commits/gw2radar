from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.promotion_action_plan import build_acquisition_promotion_action_plans
from gw2radar.acquisition.promotion_readiness import build_acquisition_promotion_readiness_report
from gw2radar.acquisition.promotion_workflow import build_acquisition_promotion_workflow


class AcquisitionPromotionManifestArtifact(BaseModel):
    artifact_id: str
    schema_version: str
    endpoint: str
    purpose: str


class AcquisitionPromotionReleaseManifest(BaseModel):
    schema_version: str = "gw2radar.acquisition_promotion_release_manifest.v1"
    generated_at: str
    release_ready: bool
    promotion_ready: bool
    workflow_ready: bool
    maturity_label: str
    overall_score: float
    queue_item_count: int
    action_plan_count: int
    blocker_count: int
    warning_count: int
    artifacts: list[AcquisitionPromotionManifestArtifact]
    evidence_chain: list[str] = Field(default_factory=list)
    operator_steps: list[str] = Field(default_factory=list)
    safety_boundary: list[str] = Field(default_factory=list)


def build_acquisition_promotion_release_manifest(session: Session) -> AcquisitionPromotionReleaseManifest:
    readiness = build_acquisition_promotion_readiness_report(session)
    workflow = build_acquisition_promotion_workflow(session)
    action_plans = build_acquisition_promotion_action_plans(session)
    artifacts = [
        AcquisitionPromotionManifestArtifact(
            artifact_id="promotion_readiness",
            schema_version=readiness.schema_version,
            endpoint="/api/v1/acquisition/promotion-readiness",
            purpose="Release gate for acquisition promotion blockers and warnings.",
        ),
        AcquisitionPromotionManifestArtifact(
            artifact_id="promotion_workflow",
            schema_version=workflow.schema_version,
            endpoint="/api/v1/acquisition/promotion-workflow",
            purpose="Front-end friendly operator queue and maturity summary.",
        ),
        AcquisitionPromotionManifestArtifact(
            artifact_id="promotion_action_plans",
            schema_version=action_plans.schema_version,
            endpoint="/api/v1/acquisition/promotion-action-plans",
            purpose="Per-item operator checklist, evidence requirements, and review gates.",
        ),
    ]
    return AcquisitionPromotionReleaseManifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        release_ready=readiness.ready and workflow.ready,
        promotion_ready=readiness.ready,
        workflow_ready=workflow.ready,
        maturity_label=workflow.maturity_label,
        overall_score=workflow.overall_score,
        queue_item_count=workflow.queue_item_count,
        action_plan_count=action_plans.plan_count,
        blocker_count=len(workflow.blockers),
        warning_count=len(workflow.warnings),
        artifacts=artifacts,
        evidence_chain=[
            "/api/v1/acquisition/evidence-coverage",
            "/api/v1/acquisition/maturity",
            "/api/v1/acquisition/promotion-queue",
            "/api/v1/acquisition/promotion-readiness",
            "/api/v1/acquisition/promotion-workflow",
            "/api/v1/acquisition/promotion-action-plans",
        ],
        operator_steps=workflow.next_operator_steps,
        safety_boundary=[
            "Manifest is read-only and does not publish, persist, import, enable, or disable rules.",
            "Release requires human review of blockers, warnings, and action-plan gates.",
            "Source handling remains summary-only with attribution; no full-text copying is allowed.",
            "No private player data, automated trading, or guaranteed market outcome claims are allowed.",
        ],
    )


def render_acquisition_promotion_release_manifest_markdown(
    manifest: AcquisitionPromotionReleaseManifest,
) -> str:
    lines = [
        "# Acquisition Promotion Release Manifest",
        "",
        f"- schema_version: `{manifest.schema_version}`",
        f"- generated_at: `{manifest.generated_at}`",
        f"- release_ready: `{str(manifest.release_ready).lower()}`",
        f"- promotion_ready: `{str(manifest.promotion_ready).lower()}`",
        f"- workflow_ready: `{str(manifest.workflow_ready).lower()}`",
        f"- maturity_label: `{manifest.maturity_label}`",
        f"- overall_score: `{manifest.overall_score:.3f}`",
        f"- queue_item_count: `{manifest.queue_item_count}`",
        f"- action_plan_count: `{manifest.action_plan_count}`",
        f"- blocker_count: `{manifest.blocker_count}`",
        f"- warning_count: `{manifest.warning_count}`",
        "",
        "## Artifacts",
        "",
        "| Artifact | Schema | Endpoint | Purpose |",
        "|---|---|---|---|",
    ]
    for artifact in manifest.artifacts:
        lines.append(
            f"| {artifact.artifact_id} | {artifact.schema_version} | "
            f"{artifact.endpoint} | {artifact.purpose} |"
        )
    lines.extend(["", "## Evidence Chain", ""])
    lines.extend(f"- {item}" for item in manifest.evidence_chain)
    lines.extend(["", "## Operator Steps", ""])
    lines.extend(f"- {step}" for step in manifest.operator_steps) if manifest.operator_steps else lines.append("- none")
    lines.extend(["", "## Safety Boundary", ""])
    lines.extend(f"- {note}" for note in manifest.safety_boundary)
    return "\n".join(lines) + "\n"
