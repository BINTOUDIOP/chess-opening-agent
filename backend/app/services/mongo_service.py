# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

"""
mongo_service.py
-
Service MongoDB pour :
- Cache des réponses agent (TTL 1h)
- Historique des parties des joueurs
"""

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoService:

    def __init__(self):
        self._client: AsyncIOMotorClient | None = None

    def _get_db(self):
        if self._client is None:
            self._client = AsyncIOMotorClient(settings.mongodb_uri)
        return self._client[settings.mongodb_db]

    async def ensure_indexes(self) -> None:
        """Crée les index MongoDB au démarrage (TTL 1h sur le cache agent)."""
        try:
            db = self._get_db()
            await db.agent_cache.create_index([("cached_at", 1)], expireAfterSeconds=3600)
            logger.info("Index MongoDB initialisés (TTL cache : 1h)")
        except Exception as e:
            logger.warning(f"Impossible de créer les index MongoDB : {e}")

    # - Cache agent -

    async def get_cached_response(self, fen: str) -> dict | None:
        """Retourne la réponse cachée pour un FEN donné, ou None si absente/expirée."""
        try:
            db  = self._get_db()
            doc = await db.agent_cache.find_one({"fen": fen})
            return doc.get("response") if doc else None
        except Exception as e:
            logger.warning(f"Cache miss (erreur Mongo) : {e}")
            return None

    async def set_cached_response(self, fen: str, response: dict) -> None:
        """Met en cache la réponse de l'agent pour un FEN (TTL géré par index MongoDB)."""
        try:
            db = self._get_db()
            await db.agent_cache.replace_one(
                {"fen": fen},
                {"fen": fen, "response": response, "cached_at": datetime.utcnow()},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Impossible de mettre en cache : {e}")

    # - Historique des parties -

    async def save_move(self, session_id: str, fen: str, move: str, source: str) -> None:
        """Enregistre un coup joué dans l'historique."""
        try:
            db = self._get_db()
            await db.games.insert_one({
                "session_id": session_id,
                "fen":        fen,
                "move":       move,
                "source":     source,
                "played_at":  datetime.utcnow(),
            })
        except Exception as e:
            logger.error(f"Erreur sauvegarde coup : {e}")

    async def get_game_history(self, session_id: str) -> list:
        """Retourne l'historique des coups d'une session."""
        try:
            db     = self._get_db()
            cursor = db.games.find(
                {"session_id": session_id},
                {"_id": 0},
                sort=[("played_at", 1)],
            )
            return await cursor.to_list(length=200)
        except Exception as e:
            logger.error(f"Erreur récupération historique : {e}")
            return []

mongo_service = MongoService()
