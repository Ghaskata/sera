from fastapi import APIRouter

from app.connectors.catalog import CONNECTOR_CATALOG

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("/catalog")
def connector_catalog() -> list[dict]:
    return [
        {
            "provider": definition.provider,
            "display_name": definition.display_name,
            "auth_family": definition.auth_family,
            "capabilities": list(definition.capabilities),
            "status": definition.status,
            "setup_mode": definition.setup_mode,
            "note": definition.note,
        }
        for definition in CONNECTOR_CATALOG
    ]
