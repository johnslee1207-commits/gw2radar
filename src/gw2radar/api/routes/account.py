from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter
from fastapi.responses import Response

from gw2radar.api import state
from gw2radar.api.state import delete_account_snapshot, reset_cached_graph
from gw2radar.commercial.build_fit import list_character_snapshots
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.ingest.account_sync_coordinator import AccountSyncCoordinator
from gw2radar.ingest.gw2_api_client import Gw2ApiClientError, Gw2ApiRateLimitError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.security.api_key_permissions import build_missing_key_permission_report, build_permission_report
from gw2radar.security.api_key_store import EncryptedApiKeyStore
from gw2radar.support.account_debug_bundle_audit import (
    build_support_review_metrics,
    create_support_review_audit,
    list_support_review_audits,
    render_support_review_audit_csv,
)
from gw2radar.support.account_debug_bundle_review import review_account_debug_bundle

router = APIRouter(prefix="/account", tags=["account"])
permission_gateway_factory = Gw2ApiGateway


class ApiKeyRequest(BaseModel):
    api_key: str


class DebugBundleRequest(BaseModel):
    active_view: str | None = None
    active_build_id: str | None = None
    player_intent: str | None = None
    report_history_count: int = 0


class DebugBundleAuditRequest(BaseModel):
    bundle: dict
    reviewer: str | None = None
    reply_template: str | None = None
    source: str = "support_workbench"


@router.get("/api-key/status")
def get_api_key_status() -> dict:
    return _with_key_store(lambda store: store.status().__dict__)


@router.get("/api-key/permissions")
def get_api_key_permissions() -> dict:
    return _with_key_store(_inspect_permissions)


@router.get("/diagnostic")
def get_account_connection_diagnostic() -> dict:
    return _with_key_store(_build_account_connection_diagnostic)


@router.post("/debug-bundle")
def post_account_debug_bundle(request: DebugBundleRequest) -> dict:
    def build_bundle(store: EncryptedApiKeyStore) -> dict:
        diagnostic = _build_account_connection_diagnostic(store)
        return {
            "schema_version": "gw2radar.account_debug_bundle.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "client_state": {
                "active_view": request.active_view,
                "active_build_id_present": bool(request.active_build_id),
                "player_intent": request.player_intent,
                "report_history_count": max(0, int(request.report_history_count or 0)),
            },
            "key_status": diagnostic["key_status"],
            "permission_summary": {
                "schema_version": diagnostic["permission_report"].get("schema_version"),
                "key_configured": diagnostic["permission_report"].get("key_configured"),
                "limited_mode": diagnostic["permission_report"].get("limited_mode"),
                "missing_required_permissions": diagnostic["permission_report"].get("missing_required_permissions", []),
                "missing_optional_permissions": diagnostic["permission_report"].get("missing_optional_permissions", []),
                "feature_impacts": diagnostic["permission_report"].get("feature_impacts", []),
                "assumptions": diagnostic["permission_report"].get("assumptions", []),
            },
            "sync_summary": {
                "status": diagnostic["sync_status"].get("status"),
                "counts": diagnostic["sync_status"].get("counts", {}),
                "endpoint_progress": diagnostic["sync_status"].get("endpoint_progress", []),
                "latest": diagnostic["sync_status"].get("latest", []),
            },
            "diagnostic_summary": {
                "summary_status": diagnostic["summary_status"],
                "checks": diagnostic["checks"],
                "next_actions": diagnostic["next_actions"],
            },
            "snapshot_summary": diagnostic["snapshot_summary"],
            "redaction_policy": [
                "Raw API keys are excluded.",
                "Private item, material, bank, wallet, achievement, and character equipment payloads are excluded.",
                "Only counts, statuses, missing permissions, endpoint progress, and UI state flags are included.",
            ],
            "boundary": "Privacy-safe debug bundle for account connection troubleshooting.",
        }

    return _with_key_store(build_bundle)


@router.post("/debug-bundle/review")
def post_account_debug_bundle_review(bundle: dict) -> dict:
    return review_account_debug_bundle(bundle).model_dump(mode="json")


@router.post("/debug-bundle/review/audit")
def post_account_debug_bundle_review_audit(request: DebugBundleAuditRequest) -> dict:
    def write_audit(store: EncryptedApiKeyStore) -> dict:
        review = review_account_debug_bundle(request.bundle)
        record = create_support_review_audit(
            store.session,
            review=review,
            reviewer=request.reviewer,
            reply_template=request.reply_template,
            source=request.source,
        )
        return {
            "schema_version": "gw2radar.account_debug_bundle_review_audit_result.v1",
            "review": review.model_dump(mode="json"),
            "audit_record": record.model_dump(mode="json"),
            "boundary": "Audit stores review metadata and reply summary only; raw bundles and raw API keys are not stored.",
        }

    return _with_key_store(write_audit)


@router.get("/debug-bundle/review/audit", response_model=None)
def get_account_debug_bundle_review_audit(
    limit: int = 20,
    status: str | None = None,
    severity: str | None = None,
    reviewer: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    format: str = "json",
):
    def read_audits(store: EncryptedApiKeyStore):
        records = list_support_review_audits(
            store.session,
            limit=limit,
            status=status,
            severity=severity,
            reviewer=reviewer,
            created_from=_parse_optional_datetime(created_from),
            created_to=_parse_optional_datetime(created_to),
        )
        if format == "csv":
            return Response(
                content=render_support_review_audit_csv(records),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="support_review_audit.csv"'},
            )
        return {
            "schema_version": "gw2radar.account_debug_bundle_review_audit_list.v1",
            "records": [record.model_dump(mode="json") for record in records],
            "filters": {
                "limit": limit,
                "status": status,
                "severity": severity,
                "reviewer": reviewer,
                "created_from": created_from,
                "created_to": created_to,
            },
            "boundary": "Audit records exclude raw bundles, raw API keys, and private account payloads.",
        }

    return _with_key_store(read_audits)


@router.get("/debug-bundle/review/audit/metrics")
def get_account_debug_bundle_review_audit_metrics(
    limit: int = 100,
    status: str | None = None,
    severity: str | None = None,
    reviewer: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
) -> dict:
    def read_metrics(store: EncryptedApiKeyStore) -> dict:
        records = list_support_review_audits(
            store.session,
            limit=limit,
            status=status,
            severity=severity,
            reviewer=reviewer,
            created_from=_parse_optional_datetime(created_from),
            created_to=_parse_optional_datetime(created_to),
        )
        metrics = build_support_review_metrics(records)
        return {
            **metrics.model_dump(mode="json"),
            "filters": {
                "limit": limit,
                "status": status,
                "severity": severity,
                "reviewer": reviewer,
                "created_from": created_from,
                "created_to": created_to,
            },
        }

    return _with_key_store(read_metrics)


@router.put("/api-key")
def put_api_key(request: ApiKeyRequest) -> dict:
    return _with_key_store(lambda store: store.set(request.api_key).__dict__)


@router.delete("/api-key")
def delete_api_key() -> dict:
    return _with_key_store(lambda store: store.delete().__dict__)


@router.delete("/snapshot")
def delete_snapshot() -> dict:
    deleted = delete_account_snapshot()
    reset_cached_graph()
    return {"status": "deleted", "deleted": deleted}


def _with_key_store(callback):
    init_db()
    with db_session.SessionLocal() as session:
        return callback(EncryptedApiKeyStore(session))


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _build_account_connection_diagnostic(store: EncryptedApiKeyStore) -> dict:
    key_status = store.status().__dict__
    permission_report = _inspect_permissions(store)
    graph = state.get_graph()
    has_key = key_status["is_configured"]
    sync_status = AccountSyncCoordinator(
        session=store.session,
        graph_loader=state.get_graph,
        graph_saver=state.save_graph,
        gateway=permission_gateway_factory(),
    ).status()
    snapshots = list_character_snapshots(graph)
    synced_snapshots = [snapshot for snapshot in snapshots if snapshot.source == "synced_official_api"]
    synced_gear_count = sum(len(snapshot.gear) for snapshot in synced_snapshots)
    private_state_count = sum(1 for item in graph.player_state if item.graph_layer is GraphLayer.PRIVATE_PLAYER_STATE)
    checks = [
        _diagnostic_check(
            "api_key_stored",
            "API key stored",
            key_status["is_configured"],
            "API key is stored and masked.",
            "No API key is stored. Save a read-only GW2 API key first.",
            fix_action_id="focus_api_key_input",
            fix_label="Paste key",
            severity="critical",
        ),
        _diagnostic_check(
            "permissions_ready",
            "Required permissions ready",
            key_status["is_configured"] and permission_report.get("limited_mode") is False,
            "Required permissions are present for account-aware features.",
            _permissions_failure_message(permission_report),
            warn=_permission_check_is_temporarily_unavailable(permission_report),
            fix_action_id="focus_api_key_input",
            fix_label="Update key",
            severity="critical",
            details={
                "missing_required_permissions": permission_report.get("missing_required_permissions", []),
                "missing_optional_permissions": permission_report.get("missing_optional_permissions", []),
                "limited_mode": permission_report.get("limited_mode"),
            },
        ),
        _diagnostic_check(
            "sync_job_visible",
            "Sync queue visible",
            bool(sync_status.get("latest")) or sync_status.get("counts", {}).get("succeeded", 0) > 0,
            "An account sync job is visible in queue history.",
            "No account sync job is visible. Run Sync now, then re-run this diagnostic.",
            warn=key_status["is_configured"],
            fix_action_id="enqueueSync",
            fix_label="Sync now",
            severity="warning",
        ),
        _diagnostic_check(
            "private_snapshot_written",
            "Private account snapshot written",
            private_state_count > 0,
            f"{private_state_count} private player-state records are available.",
            "No private account snapshot is available yet. Drain one sync job after queueing.",
            warn=key_status["is_configured"],
            fix_action_id="drainSync",
            fix_label="Drain one job",
            severity="warning",
            details={"private_player_state_count": private_state_count},
        ),
        _diagnostic_check(
            "synced_character_snapshot",
            "Synced character snapshot available",
            bool(synced_snapshots),
            f"{len(synced_snapshots)} synced official character snapshots are available.",
            "Build Fit only has manual sample snapshots. Sync character details before using account gear.",
            warn=has_key,
            fix_action_id="enqueueSync",
            fix_label="Resync account",
            severity="warning",
            details={
                "synced_character_snapshot_count": len(synced_snapshots),
                "manual_snapshot_count": len(snapshots) - len(synced_snapshots),
            },
        ),
        _diagnostic_check(
            "build_fit_bridge_ready",
            "Build Fit gear bridge ready",
            synced_gear_count > 0,
            f"{synced_gear_count} synced gear entries can be converted for Build Fit.",
            "No synced gear entries are available for Build Fit conversion.",
            warn=has_key,
            fix_action_id="loadCharacterSnapshots",
            fix_label="Load snapshots",
            severity="warning",
            details={"synced_gear_count": synced_gear_count},
        ),
    ]
    return {
        "schema_version": "gw2radar.account_connection_diagnostic.v1",
        "summary_status": _diagnostic_summary_status(checks),
        "checks": checks,
        "key_status": key_status,
        "permission_report": permission_report,
        "sync_status": sync_status,
        "snapshot_summary": {
            "private_player_state_count": private_state_count,
            "synced_character_snapshot_count": len(synced_snapshots),
            "manual_snapshot_count": len(snapshots) - len(synced_snapshots),
            "synced_gear_count": synced_gear_count,
        },
        "next_actions": _diagnostic_next_actions(checks),
        "boundary": "Read-only diagnostic. Raw API keys and private item payloads are not returned.",
    }


def _inspect_permissions(store: EncryptedApiKeyStore) -> dict:
    api_key = store.get()
    if not api_key:
        return build_missing_key_permission_report().model_dump(mode="json")

    gateway = permission_gateway_factory()
    try:
        tokeninfo_payload = gateway._fetch_tokeninfo(api_key, request_id="account:permissions:tokeninfo")
    except Gw2ApiRateLimitError:
        report = build_missing_key_permission_report().model_copy(
            update={
                "key_configured": True,
                "assumptions": ["Tokeninfo permission check is rate limited; try again later."],
            }
        )
        return report.model_dump(mode="json")
    except Gw2ApiClientError as error:
        report = build_missing_key_permission_report().model_copy(
            update={
                "key_configured": True,
                "assumptions": [f"Tokeninfo permission check failed with {error.error_code}."],
            }
        )
        return report.model_dump(mode="json")

    return build_permission_report(tokeninfo_payload).model_dump(mode="json")


def _diagnostic_check(
    check_id: str,
    label: str,
    passed: bool,
    pass_message: str,
    fail_message: str,
    *,
    warn: bool = False,
    fix_action_id: str | None = None,
    fix_label: str | None = None,
    severity: str = "warning",
    details: dict | None = None,
) -> dict:
    status = "pass" if passed else "warn" if warn else "fail"
    return {
        "check_id": check_id,
        "label": label,
        "status": status,
        "severity": "none" if status == "pass" else severity,
        "player_message": pass_message if passed else fail_message,
        "fix_action_id": None if status == "pass" else fix_action_id,
        "fix_label": None if status == "pass" else fix_label,
        "details": details or {},
    }


def _diagnostic_summary_status(checks: list[dict]) -> str:
    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        return "blocked"
    if "warn" in statuses:
        return "needs_sync"
    return "ready"


def _diagnostic_next_actions(checks: list[dict]) -> list[str]:
    actions = []
    for check in checks:
        if check["status"] == "pass":
            continue
        if check["check_id"] == "api_key_stored":
            actions.append("Save a GW2 API key, then check permissions.")
        elif check["check_id"] == "permissions_ready":
            actions.append("Create or update the GW2 API key with account, characters, inventories, wallet, and progression permissions.")
        elif check["check_id"] == "sync_job_visible":
            actions.append("Run Sync now to queue an account snapshot job.")
        elif check["check_id"] == "private_snapshot_written":
            actions.append("Drain one sync job in local development, then refresh the diagnostic.")
        elif check["check_id"] == "synced_character_snapshot":
            actions.append("Confirm character permission and rerun account sync so character detail can be saved.")
        elif check["check_id"] == "build_fit_bridge_ready":
            actions.append("Load character snapshots in Build Fit after sync completes.")
    return actions or ["Account connection, sync, and Build Fit bridge are ready."]


def _permissions_failure_message(permission_report: dict) -> str:
    missing = permission_report.get("missing_required_permissions", [])
    if missing:
        return f"Missing required GW2 API key permissions: {', '.join(missing)}."
    assumptions = permission_report.get("assumptions", [])
    if assumptions:
        return str(assumptions[0])
    return "Required permissions are missing or could not be checked."


def _permission_check_is_temporarily_unavailable(permission_report: dict) -> bool:
    return bool(permission_report.get("key_configured")) and not permission_report.get("missing_required_permissions") and bool(
        permission_report.get("assumptions")
    )
