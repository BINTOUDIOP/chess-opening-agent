# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

from fastapi import APIRouter, HTTPException, Query
from app.services.youtube_service import youtube_service

router = APIRouter(tags=["Videos"])

@router.get("/videos/{opening:path}", summary="Vidéos YouTube pour une ouverture d'échecs")
async def get_videos(
    opening: str,
    max_results: int = Query(default=5, ge=1, le=10, description="Nombre de vidéos à retourner"),
):
    """
    Recherche des vidéos YouTube explicatives pour une ouverture donnée.

    Retourne pour chaque vidéo :
    - Titre, chaîne, miniature
    - URL directe et URL d'embed (pour intégration Angular)
    - Nombre de vues
    - Indicateur de chaîne de confiance (GothamChess, Naroditsky, etc.)

    - **opening** : Nom de l'ouverture (ex: "Sicilienne Najdorf", "Ruy Lopez", "Gambit Dame")
    """
    if not opening.strip():
        raise HTTPException(status_code=400, detail="Le nom de l'ouverture ne peut pas être vide.")
    try:
        videos = await youtube_service.search_videos(
            opening=opening,
            max_results=max_results,
        )
        if not videos:
            return {
                "opening":  opening,
                "count":    0,
                "videos":   [],
                "message":  "Aucune vidéo trouvée pour cette ouverture.",
            }
        return {
            "opening": opening,
            "count":   len(videos),
            "videos":  videos,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue : {str(e)}")
