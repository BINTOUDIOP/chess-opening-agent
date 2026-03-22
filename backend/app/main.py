# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import health, moves, evaluate, videos, search, agent
from app.core.config import settings
from app.services.mongo_service import mongo_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo_service.ensure_indexes()
    yield

app = FastAPI(
    title="FFE Chess Agent API",
    description="Agent IA pour l'apprentissage des ouvertures aux échecs - Fédération Française des Échecs",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS pour le frontend Angular (configurable via CORS_ORIGINS dans .env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routes
app.include_router(health.router,    prefix="/api/v1")
app.include_router(moves.router,     prefix="/api/v1")
app.include_router(evaluate.router,  prefix="/api/v1")
app.include_router(videos.router,    prefix="/api/v1")
app.include_router(search.router,    prefix="/api/v1")
app.include_router(agent.router,     prefix="/api/v1")
