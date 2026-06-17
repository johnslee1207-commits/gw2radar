from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["player-ui"])

_UI_ROOT = Path(__file__).resolve().parents[2] / "ui" / "static"


@router.get("/player", include_in_schema=False)
def get_player_ui() -> FileResponse:
    return FileResponse(_UI_ROOT / "player.html", media_type="text/html; charset=utf-8")
