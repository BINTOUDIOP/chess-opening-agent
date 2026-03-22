# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP


from fastapi import APIRouter, HTTPException
from app.services.lichess_service import lichess_service
from app.services.stockfish_service import stockfish_service

router = APIRouter(tags=["Moves"])

@router.get("/moves/{fen:path}", summary="Coups théoriques pour une position FEN")
async def get_moves(fen: str):
    """
    Retourne les coups théoriques depuis la base de données Lichess Masters.
    Si aucun coup n'est trouvé (position hors théorie), bascule automatiquement
    sur Stockfish pour proposer le meilleur coup calculé.

    - **fen** : Position en notation FEN (URL-encodée si nécessaire)
    """
    # Appel Lichess
    try:
        data = await lichess_service.get_moves(fen)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Si Lichess ne connaît pas la position -> Stockfish prend le relais
    if not data["moves"]:
        try:
            stockfish_data = await stockfish_service.get_best_move(fen)
            return {
                "fen": fen,
                "source": "stockfish",
                "opening": None,
                "moves": [],
                "stockfish_suggestion": stockfish_data,
                "message": "Position hors théorie - suggestion Stockfish.",
            }
        except (ValueError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {
        "fen": fen,
        "source": "lichess",
        **data,
    }
