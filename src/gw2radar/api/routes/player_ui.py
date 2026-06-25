from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["player-ui"])

_UI_ROOT = Path(__file__).resolve().parents[2] / "ui" / "static"


@router.get("/player", include_in_schema=False)
def get_player_ui() -> FileResponse:
    return FileResponse(_UI_ROOT / "player.html", media_type="text/html; charset=utf-8")


@router.get("/support", include_in_schema=False)
def get_support_ui() -> FileResponse:
    return FileResponse(_UI_ROOT / "support.html", media_type="text/html; charset=utf-8")


@router.get("/start", include_in_schema=False)
@router.get("/now", include_in_schema=False)
@router.get("/templates", include_in_schema=False)
@router.get("/help", include_in_schema=False)
@router.get("/wizard/{workflow_type}", include_in_schema=False)
@router.get("/plan/revise", include_in_schema=False)
@router.get("/report/revise", include_in_schema=False)
def get_player_os_ui() -> FileResponse:
    return FileResponse(_UI_ROOT / "player_os.html", media_type="text/html; charset=utf-8")
