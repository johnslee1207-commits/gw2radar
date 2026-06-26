from pathlib import Path

from gw2radar.commercial.report_engine import resolve_artifact_path
from gw2radar.commercial.report_productization import resolve_productized_report_artifact_path
from gw2radar.commercial.player_intelligence import (
    resolve_player_session_packet_artifact_path,
    resolve_player_support_handoff_artifact_path,
)


def test_report_engine_rejects_path_traversal() -> None:
    result = resolve_artifact_path("../../etc/passwd")
    assert result is None, "Path traversal should return None"

    result = resolve_artifact_path("foo/../../../bar")
    assert result is None

    result = resolve_artifact_path("safe-id-123")
    assert result is None or result.is_file()


def test_productized_report_rejects_path_traversal() -> None:
    result = resolve_productized_report_artifact_path("../../etc/passwd")
    assert result is None

    result = resolve_productized_report_artifact_path("safe-artifact")
    assert result is None or result.is_file()


def test_session_packet_artifact_rejects_path_traversal(tmp_path: Path) -> None:
    result = resolve_player_session_packet_artifact_path(
        "../../etc/passwd", "manifest.json", artifact_root=tmp_path
    )
    assert result is None

    result = resolve_player_session_packet_artifact_path(
        "safe-id", "../../etc/passwd", artifact_root=tmp_path
    )
    assert result is None


def test_support_handoff_artifact_rejects_traversal(tmp_path: Path) -> None:
    result = resolve_player_support_handoff_artifact_path(
        "../../etc/passwd", "support_bundle.json", artifact_root=tmp_path
    )
    assert result is None

    result = resolve_player_support_handoff_artifact_path(
        "safe-id", "nonexistent.md", artifact_root=tmp_path
    )
    assert result is None


def test_safe_slug_strips_dangerous_chars() -> None:
    from gw2radar.commercial.report_engine import _safe_slug
    assert _safe_slug("../../etc/passwd") == "etc_passwd"
    assert _safe_slug("normal-user") == "normal_user"
    assert _safe_slug("<script>") == "script"
    assert _safe_slug("") == "unknown"
