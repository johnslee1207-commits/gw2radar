from fastapi import APIRouter

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.config.settings import get_settings
from gw2radar.saas.production_foundation import build_production_saas_foundation

router = APIRouter(prefix="/api/v1/saas", tags=["saas"])


@router.get("/foundation", response_model=ApiDataEnvelope)
def get_saas_foundation() -> ApiDataEnvelope:
    foundation = build_production_saas_foundation(get_settings())
    return ApiDataEnvelope(data={"foundation": foundation.model_dump(mode="json")})
