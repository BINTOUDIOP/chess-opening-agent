# Projet : FFE Chess Agent - Proof of Concept
# Copyright (c) 2026 Bintou DIOP.

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["Health"])

@router.get("/healthcheck")
async def healthcheck():
    return {
        "status": "ok",
        "service": "FFE Chess Agent API",
        "timestamp": datetime.utcnow().isoformat(),
    }
