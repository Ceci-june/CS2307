from fastapi import APIRouter

from src.api.v1.endpoints.properties.views import view_properties
from src.api.v1.endpoints.search import view_search

router = APIRouter()

router.include_router(router=view_properties.router, prefix="/properties", tags=["Properties"],)
router.include_router(router=view_search.router, prefix="/search", tags=["Search"])
