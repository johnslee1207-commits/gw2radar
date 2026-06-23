from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.commercial.report_engine import (
    ReportEntitlementType,
    ReportExportFormat,
    ReportProduct,
    create_report_entitlement,
    generate_report_job,
    generate_report_preview,
    has_report_entitlement,
    list_report_products,
)
from gw2radar.commercial.report_productization import (
    build_productized_report_delivery_checklist,
    generate_productized_report_artifact,
    get_productized_report_template,
)
from gw2radar.db.models import ReportExportJobModel
from gw2radar.graph.graph_query import GraphData


class ReportProductContract(BaseModel):
    schema_version: str = "gw2radar.report_product_contract.v1"
    product_id: str
    name: str
    report_type: str
    tier: str
    price_cents: int | None
    preview_contract: dict
    full_report_contract: dict
    entitlement_contract: dict
    delivery_contract: dict
    safety_boundaries: list[str] = Field(default_factory=list)


class MockLicenseGrant(BaseModel):
    schema_version: str = "gw2radar.mock_report_license_grant.v1"
    product_id: str
    user_id: str
    entitlement_id: str | None
    entitlement_type: str
    granted: bool
    already_entitled: bool
    payment_provider: str = "mock"
    boundary: str = "Mock license grant is local-only and does not call a real payment provider."


class ReportCloseLoopReadiness(BaseModel):
    schema_version: str = "gw2radar.report_close_loop_readiness.v1"
    ready: bool
    product_count: int
    entitled_product_count: int
    full_report_job_count: int
    delivery_ready: bool
    missing_gates: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)


def build_report_product_contracts(session: Session, user_id: str) -> list[ReportProductContract]:
    return [_contract_for_product(session, product, user_id) for product in list_report_products(session)]


def grant_mock_report_license(
    session: Session,
    *,
    user_id: str,
    product_id: str,
    entitlement_type: ReportEntitlementType = ReportEntitlementType.FULL,
) -> MockLicenseGrant:
    _require_product(session, product_id)
    already_entitled = has_report_entitlement(session, user_id, product_id)
    entitlement = None
    if not already_entitled:
        entitlement = create_report_entitlement(session, user_id, product_id, entitlement_type)
    return MockLicenseGrant(
        product_id=product_id,
        user_id=user_id,
        entitlement_id=entitlement.entitlement_id if entitlement else None,
        entitlement_type=entitlement_type.value,
        granted=True,
        already_entitled=already_entitled,
    )


def build_report_close_loop_preview(
    session: Session,
    graph: GraphData,
    *,
    user_id: str,
    product_id: str,
    goal_id: str,
    output_root: Path = Path("outputs") / "reports",
) -> dict:
    product = _require_product(session, product_id)
    preview = generate_report_preview(
        graph,
        goal_id,
        report_type=product.report_type,
        output_root=output_root,
    )
    return {
        "schema_version": "gw2radar.report_close_loop_preview.v1",
        "product_contract": _contract_for_product(session, product, user_id).model_dump(mode="json"),
        "preview": preview,
        "boundary": "Preview output intentionally excludes paid-only tables and full report artifacts.",
    }


def generate_report_close_loop_full(
    session: Session,
    graph: GraphData,
    *,
    user_id: str,
    product_id: str,
    goal_id: str,
    export_format: ReportExportFormat = ReportExportFormat.MARKDOWN,
    knowledge_backed: bool = False,
) -> dict:
    product = _require_product(session, product_id)
    job = generate_report_job(
        session,
        graph,
        user_id=user_id,
        product_id=product_id,
        goal_id=goal_id,
        export_format=export_format,
        knowledge_backed=knowledge_backed,
    )
    delivery_artifact = None
    template_id = _template_for_product(product_id)
    if template_id is not None:
        delivery_format = _productized_format(export_format)
        delivery_artifact = generate_productized_report_artifact(
            session,
            graph,
            user_id=user_id,
            template_id=template_id,
            export_format=delivery_format,
        ).model_dump(mode="json")
    return {
        "schema_version": "gw2radar.report_close_loop_full_generation.v1",
        "product_contract": _contract_for_product(session, product, user_id).model_dump(mode="json"),
        "job": job.model_dump(mode="json"),
        "delivery_artifact": delivery_artifact,
        "boundary": "Full report generation requires entitlement and remains manual-action-only.",
    }


def build_report_close_loop_workflow(
    session: Session,
    graph: GraphData,
    *,
    user_id: str,
    product_id: str,
    goal_id: str,
    export_format: ReportExportFormat = ReportExportFormat.MARKDOWN,
    grant_mock_license: bool = False,
    include_preview: bool = True,
) -> dict:
    product = _require_product(session, product_id)
    preview = None
    if include_preview:
        preview = build_report_close_loop_preview(
            session,
            graph,
            user_id=user_id,
            product_id=product_id,
            goal_id=goal_id,
        )
    license_grant = None
    if grant_mock_license:
        license_grant = grant_mock_report_license(session, user_id=user_id, product_id=product_id)
    generation = None
    if has_report_entitlement(session, user_id, product_id):
        generation = generate_report_close_loop_full(
            session,
            graph,
            user_id=user_id,
            product_id=product_id,
            goal_id=goal_id,
            export_format=export_format,
        )
    return {
        "schema_version": "gw2radar.report_close_loop_workflow.v1",
        "product_contract": _contract_for_product(session, product, user_id).model_dump(mode="json"),
        "preview": preview,
        "license_grant": license_grant.model_dump(mode="json") if license_grant else None,
        "generation": generation,
        "readiness": build_report_close_loop_readiness(session, user_id).model_dump(mode="json"),
        "safety_boundaries": _safety_boundaries(),
    }


def build_report_close_loop_readiness(session: Session, user_id: str) -> ReportCloseLoopReadiness:
    products = list_report_products(session)
    entitled_count = sum(1 for product in products if has_report_entitlement(session, user_id, product.product_id))
    job_count = session.query(ReportExportJobModel).filter(ReportExportJobModel.user_id == user_id).count()
    delivery = build_productized_report_delivery_checklist()
    missing_gates: list[str] = []
    if not products:
        missing_gates.append("Register report products.")
    if entitled_count == 0:
        missing_gates.append("Grant at least one mock license or subscription entitlement before full report generation.")
    if not delivery.ready:
        missing_gates.append("Generate and verify productized delivery artifacts before manual fulfillment.")
    return ReportCloseLoopReadiness(
        ready=not missing_gates,
        product_count=len(products),
        entitled_product_count=entitled_count,
        full_report_job_count=job_count,
        delivery_ready=delivery.ready,
        missing_gates=missing_gates,
        next_actions=[
            "Use preview before purchase or license grant.",
            "Grant a mock license only in local development or deterministic tests.",
            "Generate the full report and verify delivery artifacts before handoff.",
        ],
        safety_boundaries=_safety_boundaries(),
    )


def _contract_for_product(session: Session, product: ReportProduct, user_id: str) -> ReportProductContract:
    entitled = has_report_entitlement(session, user_id, product.product_id)
    template = _template_for_product(product.product_id)
    return ReportProductContract(
        product_id=product.product_id,
        name=product.name,
        report_type=product.report_type,
        tier=product.tier.value,
        price_cents=product.price_cents,
        preview_contract={
            "available": True,
            "render_mode": "preview",
            "paid_only_detail_hidden": True,
            "requires_entitlement": False,
        },
        full_report_contract={
            "available": True,
            "render_mode": "full",
            "requires_entitlement": product.tier.value != "free",
            "has_entitlement": entitled,
            "supported_formats": [item.value for item in ReportExportFormat],
        },
        entitlement_contract={
            "payment_provider": "mock",
            "real_payment_provider_enabled": False,
            "grant_endpoint": "/api/v1/reports/close-loop/mock-license",
            "entitlement_required": product.tier.value != "free",
        },
        delivery_contract={
            "shared_lifecycle": True,
            "productized_template_id": template,
            "artifact_bundle_endpoint": "/api/v1/reports/productized/artifacts/bundle",
            "delivery_checklist_endpoint": "/api/v1/reports/productized/delivery-checklist",
        },
        safety_boundaries=_safety_boundaries(),
    )


def _require_product(session: Session, product_id: str) -> ReportProduct:
    products = {product.product_id: product for product in list_report_products(session)}
    if product_id not in products:
        raise ValueError("Unknown or disabled report product.")
    return products[product_id]


def _template_for_product(product_id: str) -> str | None:
    for template_id in ["account_value_analysis", "legendary_gap_analysis", "build_readiness_advisor"]:
        template = get_productized_report_template(template_id)
        if template and template.product_id == product_id:
            return template.template_id
    return None


def _productized_format(export_format: ReportExportFormat) -> str:
    if export_format == ReportExportFormat.HTML:
        return "html"
    if export_format == ReportExportFormat.ZIP:
        return "markdown"
    if export_format == ReportExportFormat.PDF:
        return "markdown"
    return "markdown"


def _safety_boundaries() -> list[str]:
    return [
        "Preview reports hide paid-only detail and require no entitlement.",
        "Full reports require a local entitlement or free product tier.",
        "Mock license grants do not call real payment providers.",
        "Delivery artifacts use checksumed local files and manual handoff.",
        "Reports must not include raw API keys, raw private payloads, automatic trading, or guaranteed outcomes.",
    ]
