"""
Aggregate API routes.
"""
from fastapi import APIRouter

from app.api.routes import auth, chat, health, logs, sessions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(sessions.router)
api_router.include_router(sessions.legacy_router)
api_router.include_router(logs.router)
