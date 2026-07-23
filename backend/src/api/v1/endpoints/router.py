from fastapi import APIRouter

from src.api.v1.endpoints.properties.views import view_properties

router = APIRouter()

router.include_router(router=view_properties.router, prefix="/properties", tags=["Properties"],)
