# Projet : FFE Chess Agent - Proof of Concept
# Copyright (c) 2026 Bintou DIOP.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.chess_graph import chess_agent
from app.services.mongo_service import mongo_service

router = APIRouter(tags=["Agent"])

class AgentRequest(BaseModel):
    fen: str

@router.post("/agent", summary="Agent IA complet - analyse une position FEN")
async def run_agent(request: AgentRequest):
    """
    Point d'entrée principal de l'agent IA.
    Orchestre automatiquement :
    1. Validation FEN
    2. Coups théoriques Lichess
    3. Fallback Stockfish si hors théorie
    4. Contexte RAG Milvus + vidéos YouTube
    5. Explication pédagogique Mistral Large
    Les réponses sont mises en cache dans MongoDB (TTL 1h).
    """
    # Vérification du cache avant d'invoquer le graph
    cached = await mongo_service.get_cached_response(request.fen)
    if cached:
        return cached

    initial_state = {
        "fen": request.fen,
        "is_valid": False,
        "error": None,
        "lichess_moves": [],
        "opening_name": None,
        "opening_eco": None,
        "stockfish_result": None,
        "vector_context": None,
        "videos": [],
        "source": "lichess",
        "explanation": None,
        "response": None,
    }

    try:
        final_state = await chess_agent.ainvoke(initial_state)
        response = final_state.get("response", {})
        if "error" in response:
            raise HTTPException(status_code=400, detail=response["error"])
        # Mise en cache de la réponse
        await mongo_service.set_cached_response(request.fen, response)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent : {str(e)}")
