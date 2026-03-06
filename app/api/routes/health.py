"""
Health check endpoint for load balancers and monitoring.
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness/readiness: returns 200 when the service is up."""
    return {"status": "ok"}
