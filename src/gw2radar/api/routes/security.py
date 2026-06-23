from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.config.settings import get_settings
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.security.api_key_normalization import normalize_api_key
from gw2radar.security.crypto import fingerprint_api_key
from gw2radar.security.privacy_delete import delete_private_data
from gw2radar.security.store_factory import build_secret_store

router = APIRouter(prefix="/api/v1/security", tags=["security"])

LOCAL_USER_ID = "local-user"
CredentialMode = Literal["session_only", "encrypted_persistent", "team_workspace_placeholder"]


class SecurityApiKeyRequest(BaseModel):
    api_key: str
    mode: CredentialMode = "encrypted_persistent"


class SecurityApiKeyRotateRequest(BaseModel):
    api_key: str
    mode: CredentialMode = "encrypted_persistent"


class SessionOnlyApiKeyPreviewRequest(BaseModel):
    api_key: str


class PrivateDataDeleteRequest(BaseModel):
    delete_api_key: bool = True
    delete_account_snapshot: bool = True
    delete_private_player_state: bool = True
    delete_personal_intelligence: bool = True
    delete_exports: bool = True


@router.post("/api-key", response_model=ApiDataEnvelope)
def save_api_key(request: SecurityApiKeyRequest) -> ApiDataEnvelope:
    if request.mode == "session_only":
        return ApiDataEnvelope(data=_session_only_preview(request.api_key))
    if request.mode == "team_workspace_placeholder":
        return ApiDataEnvelope(data=_team_workspace_placeholder())
    return _with_store(
        lambda store, _session: ApiDataEnvelope(
            data={
                **store.put_api_key(
                    LOCAL_USER_ID,
                    request.api_key,
                    metadata={"credential_mode": request.mode},
                ).model_dump(mode="json"),
                "credential_mode": request.mode,
                "audit_event": _audit_event("credential_saved", request.mode),
                "safety_boundaries": _credential_safety_boundaries(request.mode),
            }
        )
    )


@router.get("/api-key/status", response_model=ApiDataEnvelope)
def get_api_key_status() -> ApiDataEnvelope:
    return _with_store(
        lambda store, _session: ApiDataEnvelope(
            data={
                **store.get_status(LOCAL_USER_ID).model_dump(mode="json"),
                "raw_key_returned": False,
                "front_end_storage_allowed": False,
                "url_transport_allowed": False,
            }
        )
    )


@router.post("/api-key/session-preview", response_model=ApiDataEnvelope)
def preview_session_only_api_key(request: SessionOnlyApiKeyPreviewRequest) -> ApiDataEnvelope:
    return ApiDataEnvelope(data=_session_only_preview(request.api_key))


@router.post("/api-key/rotate", response_model=ApiDataEnvelope)
def rotate_api_key(request: SecurityApiKeyRotateRequest) -> ApiDataEnvelope:
    if request.mode == "session_only":
        return ApiDataEnvelope(data=_session_only_preview(request.api_key, event_type="credential_rotation_previewed"))
    if request.mode == "team_workspace_placeholder":
        return ApiDataEnvelope(data=_team_workspace_placeholder())
    return _with_store(
        lambda store, _session: ApiDataEnvelope(
            data={
                **store.rotate_api_key(LOCAL_USER_ID, request.api_key).model_dump(mode="json"),
                "credential_mode": request.mode,
                "audit_event": _audit_event("credential_rotated", request.mode),
                "safety_boundaries": _credential_safety_boundaries(request.mode),
            }
        )
    )


@router.delete("/api-key", response_model=ApiDataEnvelope)
def delete_api_key() -> ApiDataEnvelope:
    return _with_store(
        lambda store, _session: ApiDataEnvelope(
            data={
                "deleted": store.delete_api_key(LOCAL_USER_ID),
                "audit_event": _audit_event("credential_revoked", "encrypted_persistent"),
                "safety_boundaries": _credential_safety_boundaries("encrypted_persistent"),
            }
        )
    )


@router.get("/credential-center", response_model=ApiDataEnvelope)
def get_credential_center() -> ApiDataEnvelope:
    def build_center(store, _session) -> ApiDataEnvelope:
        status = store.get_status(LOCAL_USER_ID).model_dump(mode="json")
        return ApiDataEnvelope(
            data={
                "schema_version": "gw2radar.credential_center.v1",
                "default_mode": "session_only",
                "recommended_mode": "session_only",
                "available_modes": [
                    _credential_mode("session_only"),
                    _credential_mode("encrypted_persistent"),
                    _credential_mode("team_workspace_placeholder"),
                ],
                "stored_credential_status": {
                    **status,
                    "raw_key_returned": False,
                    "front_end_storage_allowed": False,
                    "url_transport_allowed": False,
                },
                "provider_types": [
                    {"provider_id": "gw2_api", "status": "implemented"},
                    {"provider_id": "llm_provider", "status": "deferred"},
                    {"provider_id": "search_provider", "status": "deferred"},
                    {"provider_id": "commerce_provider", "status": "deferred"},
                ],
                "audit_summary": _audit_summary(status),
                "next_actions": [
                    "Use session-only mode when you want analysis without persisted credentials.",
                    "Use encrypted persistent mode only when weekly or repeated local reports are explicitly needed.",
                    "Use delete or rotate controls whenever you want to revoke local access.",
                ],
                "safety_boundaries": _credential_safety_boundaries("session_only"),
            }
        )

    return _with_store(build_center)


@router.get("/credential-center/permission-explanation", response_model=ApiDataEnvelope)
def get_permission_explanation() -> ApiDataEnvelope:
    return ApiDataEnvelope(
        data={
            "schema_version": "gw2radar.credential_permission_explanation.v1",
            "accessed_permissions": [
                _permission_explanation(
                    "account",
                    "Identify account-level metadata needed for account-aware summaries.",
                    ["password", "email", "ArenaNet login session"],
                ),
                _permission_explanation(
                    "characters",
                    "Read character names, profession context, and equipment summaries for Build Fit.",
                    ["game client control", "automatic gear changes"],
                ),
                _permission_explanation(
                    "wallet",
                    "Estimate currency context for value and goal planning.",
                    ["gold transfers", "commerce actions"],
                ),
                _permission_explanation(
                    "inventories",
                    "Summarize item/material holdings for value, legendary gap, and do-not-sell guidance.",
                    ["item deletion", "item sale execution"],
                ),
                _permission_explanation(
                    "progression",
                    "Read achievement/progression context for routes and returner guidance.",
                    ["achievement completion", "gameplay automation"],
                ),
                _permission_explanation(
                    "tradingpost",
                    "Optional context for existing orders only when the user grants it.",
                    ["placing orders", "canceling orders", "guaranteed profit decisions"],
                ),
            ],
            "global_safety_boundaries": _credential_safety_boundaries("session_only"),
            "manual_review_boundary": "GW2Radar can recommend review candidates, but it never trades, buys, sells, deletes items, changes gear, or controls gameplay.",
        }
    )


@router.get("/credential-center/audit", response_model=ApiDataEnvelope)
def get_credential_audit() -> ApiDataEnvelope:
    def build_audit(store, _session) -> ApiDataEnvelope:
        status = store.get_status(LOCAL_USER_ID).model_dump(mode="json")
        has_key = bool(status.get("has_api_key"))
        return ApiDataEnvelope(
            data={
                "schema_version": "gw2radar.credential_audit_summary.v1",
                "events": [
                    {
                        "event_type": "credential_status_checked",
                        "credential_mode": "encrypted_persistent" if has_key else "none",
                        "has_api_key": has_key,
                        "key_fingerprint": status.get("key_fingerprint"),
                        "raw_key_returned": False,
                        "private_payload_returned": False,
                    }
                ],
                "stored_credential_status": status,
                "revoke_endpoint": "/api/v1/security/api-key",
                "rotate_endpoint": "/api/v1/security/api-key/rotate",
                "boundary": "Credential audit is metadata-only and excludes raw API keys, raw account payloads, and provider secrets.",
            }
        )

    return _with_store(build_audit)


@router.delete("/private-data", response_model=ApiDataEnvelope)
def delete_private_account_data(request: PrivateDataDeleteRequest) -> ApiDataEnvelope:
    return _with_store(
        lambda store, session: ApiDataEnvelope(
            data=delete_private_data(
                session,
                store,
                user_id=LOCAL_USER_ID,
                delete_api_key=request.delete_api_key,
                delete_account_snapshot=request.delete_account_snapshot,
                delete_private_player_state=request.delete_private_player_state,
                delete_personal_intelligence=request.delete_personal_intelligence,
                delete_exports=request.delete_exports,
            )
        )
    )


def _with_store(callback):
    init_db()
    with db_session.SessionLocal() as session:
        store = build_secret_store(get_settings(), session)
        return callback(store, session)


def _session_only_preview(api_key: str, *, event_type: str = "credential_session_previewed") -> dict:
    clean_key = normalize_api_key(api_key)
    return {
        "schema_version": "gw2radar.session_only_credential_preview.v1",
        "credential_mode": "session_only",
        "persisted": False,
        "has_api_key": bool(clean_key),
        "key_fingerprint": fingerprint_api_key(clean_key) if clean_key else None,
        "audit_event": _audit_event(event_type, "session_only"),
        "safety_boundaries": _credential_safety_boundaries("session_only"),
        "next_action": "Run analysis in this request/session without saving the key, or explicitly choose encrypted persistent mode.",
    }


def _team_workspace_placeholder() -> dict:
    return {
        "schema_version": "gw2radar.team_workspace_credential_placeholder.v1",
        "credential_mode": "team_workspace_placeholder",
        "persisted": False,
        "status": "deferred",
        "reason": "Team workspace credential sharing is a later explicit production SaaS stage.",
        "safety_boundaries": _credential_safety_boundaries("team_workspace_placeholder"),
    }


def _credential_mode(mode: CredentialMode) -> dict:
    descriptions = {
        "session_only": "Use a pasted key only for the current request/session and do not persist it.",
        "encrypted_persistent": "Store the key encrypted in the local secret store for repeated local analysis.",
        "team_workspace_placeholder": "Deferred production SaaS mode where admins manage shared credentials.",
    }
    return {
        "mode": mode,
        "label": mode.replace("_", " ").title(),
        "implemented": mode in {"session_only", "encrypted_persistent"},
        "persists_secret": mode == "encrypted_persistent",
        "description": descriptions[mode],
        "safety_boundaries": _credential_safety_boundaries(mode),
    }


def _permission_explanation(permission: str, purpose: str, not_accessed: list[str]) -> dict:
    return {
        "permission": permission,
        "purpose": purpose,
        "not_accessed": not_accessed,
    }


def _credential_safety_boundaries(mode: str) -> list[str]:
    boundaries = [
        "Raw API keys are never returned by security API responses.",
        "API keys must not be sent in URLs, logs, generated reports, or front-end storage.",
        "GW2Radar cannot access ArenaNet passwords, email, login sessions, or the game client.",
        "GW2Radar never buys, sells, trades, deletes items, changes gear, or controls gameplay.",
    ]
    if mode == "session_only":
        boundaries.append("Session-only mode does not persist the submitted key.")
    if mode == "encrypted_persistent":
        boundaries.append("Encrypted persistent mode stores only encrypted payload plus fingerprint metadata.")
    if mode == "team_workspace_placeholder":
        boundaries.append("Team workspace credential sharing is deferred and not active in this MVP.")
    return boundaries


def _audit_event(event_type: str, mode: str) -> dict:
    return {
        "schema_version": "gw2radar.credential_audit_event.v1",
        "event_type": event_type,
        "credential_mode": mode,
        "raw_key_recorded": False,
        "private_payload_recorded": False,
    }


def _audit_summary(status: dict) -> dict:
    return {
        "schema_version": "gw2radar.credential_audit_summary.v1",
        "has_api_key": bool(status.get("has_api_key")),
        "key_fingerprint": status.get("key_fingerprint"),
        "storage_backend": status.get("storage_backend"),
        "encrypted": status.get("encrypted"),
        "raw_key_recorded": False,
        "private_payload_recorded": False,
    }
