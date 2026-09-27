"""GET /v1/metadata endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
from app.models.responses import MetadataResponse

router = APIRouter()
SUBMITTED_AT = datetime.now(timezone.utc).isoformat()


@router.get("/v1/metadata", response_model=MetadataResponse)
async def metadata():
    return MetadataResponse(
        team_name=settings.TEAM_NAME,
        team_members=settings.TEAM_MEMBERS,
        model=settings.MODEL_NAME,
        approach=settings.APPROACH,
        contact_email=settings.CONTACT_EMAIL,
        version=settings.BOT_VERSION,
        submitted_at=SUBMITTED_AT,
    )
