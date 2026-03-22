# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

"""
youtube_service.py
-
Recherche de vidéos YouTube explicatives pour une ouverture d'échecs donnée.
Utilise l'API YouTube Data v3 via google-api-python-client.
"""

import asyncio
import threading
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Chaînes YouTube de référence (échecs) - filtre de qualité
TRUSTED_CHANNELS = {
    "GothamChess",
    "Daniel Naroditsky",
    "Chess.com",
    "agadmator's Chess Channel",
    "Saint Louis Chess Club",
    "Hikaru",
    "ChessBase India",
    "Remote Chess Academy",
    "John Bartholomew",
}

class YouTubeService:
    """Recherche des vidéos YouTube pertinentes pour une ouverture d'échecs."""

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        """Lazy init thread-safe du client YouTube."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    if not settings.youtube_api_key:
                        raise RuntimeError("YOUTUBE_API_KEY manquante dans les variables d'environnement.")
                    self._client = build(
                        "youtube", "v3",
                        developerKey=settings.youtube_api_key,
                        cache_discovery=False,
                    )
        return self._client

    def _build_query(self, opening: str) -> str:
        """Construit une requête de recherche optimisée pour YouTube."""
        # On enrichit la requête avec des mots-clés pertinents
        keywords = ["chess opening", "tutorial", "explanation"]
        base = opening.strip()
        return f"{base} {keywords[0]} {keywords[1]}"

    def _is_relevant(self, title: str, description: str, opening: str) -> bool:
        """Filtre basique de pertinence par mots-clés dans le titre/description."""
        opening_lower = opening.lower()
        title_lower   = title.lower()
        desc_lower    = description.lower()

        chess_keywords = ["chess", "échecs", "opening", "ouverture", "variation", "defense", "gambit"]
        has_chess  = any(kw in title_lower or kw in desc_lower for kw in chess_keywords)
        has_topic  = any(w in title_lower for w in opening_lower.split())
        return has_chess or has_topic

    async def search_videos(self, opening: str, max_results: int = 5) -> list[dict]:
        """
        Recherche des vidéos YouTube pour une ouverture donnée.
        Exécuté dans un thread séparé pour ne pas bloquer FastAPI.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._search_sync, opening, max_results
        )

    def _search_sync(self, opening: str, max_results: int) -> list[dict]:
        """Appel synchrone à l'API YouTube."""
        try:
            youtube = self._get_client()
            query   = self._build_query(opening)

            # Recherche principale
            search_response = youtube.search().list(
                q=query,
                part="snippet",
                type="video",
                maxResults=max_results * 2,        # On prend le double pour filtrer
                relevanceLanguage="fr",            # Préférence pour le français
                videoEmbeddable="true",            # Vidéos intégrables uniquement
                videoDuration="medium",            # 4-20 min : ni trop court ni trop long
                order="relevance",
            ).execute()

            videos = []
            video_ids = []

            for item in search_response.get("items", []):
                snippet    = item["snippet"]
                video_id   = item["id"]["videoId"]
                title      = snippet.get("title", "")
                description = snippet.get("description", "")
                channel    = snippet.get("channelTitle", "")

                if not self._is_relevant(title, description, opening):
                    continue

                video_ids.append(video_id)
                videos.append({
                    "video_id":     video_id,
                    "title":        title,
                    "channel":      channel,
                    "description":  description[:200] + "..." if len(description) > 200 else description,
                    "thumbnail":    snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    "published_at": snippet.get("publishedAt"),
                    "url":          f"https://www.youtube.com/watch?v={video_id}",
                    "embed_url":    f"https://www.youtube.com/embed/{video_id}",
                    "trusted_channel": channel in TRUSTED_CHANNELS,
                })

            # Récupération des durées via videos.list
            if video_ids:
                details = youtube.videos().list(
                    part="contentDetails,statistics",
                    id=",".join(video_ids[:max_results * 2]),
                ).execute()

                duration_map = {}
                views_map    = {}
                for item in details.get("items", []):
                    vid = item["id"]
                    duration_map[vid] = item["contentDetails"].get("duration", "PT0S")
                    views_map[vid]    = int(item["statistics"].get("viewCount", 0))

                for v in videos:
                    v["duration_iso"] = duration_map.get(v["video_id"], "")
                    v["view_count"]   = views_map.get(v["video_id"], 0)

            # Tri : chaînes de confiance en premier, puis par vues
            videos.sort(key=lambda v: (
                not v.get("trusted_channel", False),
                -v.get("view_count", 0)
            ))

            return videos[:max_results]

        except HttpError as e:
            if e.resp.status == 403:
                raise RuntimeError("Quota YouTube dépassé. Réessayez demain.")
            raise RuntimeError(f"Erreur YouTube API : {e}")
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue YouTube : {e}")
            return []

youtube_service = YouTubeService()
