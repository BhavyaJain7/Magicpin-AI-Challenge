"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.context import router as context_router
from app.api.health import router as health_router
from app.api.metadata import router as metadata_router
from app.api.reply import router as reply_router
from app.api.tick import router as tick_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    yield
    # Shutdown actions


app = FastAPI(
    title="Vera Merchant AI Assistant",
    description="magicpin AI Challenge - WhatsApp Merchant AI Assistant",
    version=settings.BOT_VERSION,
    lifespan=lifespan,
)

# Enable CORS for local testing/judge harness
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all 5 API endpoints
app.include_router(health_router)
app.include_router(metadata_router)
app.include_router(context_router)
app.include_router(tick_router)
app.include_router(reply_router)
