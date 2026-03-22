# Projet : FFE Chess Agent - Proof of Concept
# Copyright (c) 2026 Bintou DIOP.

from fastapi import APIRouter, HTTPException, Query
from app.services.stockfish_service import stockfish_service

router = APIRouter(tags=["Evaluate"])

@router.get("/evaluate/{fen:path}", summary="Évaluation Stockfish d'une position FEN")
async def evaluate_position(
    fen: str,
    multipv: int = Query(default=3, ge=1, le=5, description="Nombre de lignes à analyser"),
):
    """
    Évalue une position FEN avec le moteur Stockfish.

    Retourne :
    - Le score en **centipawns** (positif = avantage Blancs, négatif = avantage Noirs)
    - Le meilleur coup en notation UCI et SAN
    - La ligne principale (PV) sur 5 coups
    - La profondeur d'analyse

    - **fen** : Position en notation FEN
    - **multipv** : Nombre de variantes retournées (1 à 5)
    """
    try:
        result = await stockfish_service.evaluate(fen)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
