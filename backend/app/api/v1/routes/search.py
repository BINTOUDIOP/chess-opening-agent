# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.milvus_service import milvus_service

router = APIRouter(tags=["Vector Search"])

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Requête de recherche sur les ouvertures")
    top_k: int = Field(default=5, ge=1, le=20, description="Nombre de résultats à retourner")

@router.post("/vector-search", summary="Recherche sémantique dans la base Wikichess (Milvus)")
async def vector_search(request: SearchRequest):
    """
    Effectue une recherche sémantique dans Milvus sur le corpus Wikichess.

    Retourne les chunks textuels les plus proches sémantiquement de la requête,
    avec leur score de similarité cosinus.

    Exemples de requêtes :
    - "comment jouer la Sicilienne Najdorf"
    - "ouverture pour les blancs contre e5"
    - "que faire si l'adversaire joue la Française"
    """
    try:
        results = await milvus_service.search(
            query=request.query,
            top_k=request.top_k,
        )
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Erreur Milvus : {str(e)}")
