"""
milvus_service.py
-
Gestion de la base vectorielle Milvus pour la recherche sémantique
sur les données Wikichess (ouvertures aux échecs).

Modèle d'embedding : sentence-transformers (all-MiniLM-L6-v2)
Dimension des vecteurs : 384
"""

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

# Dimensions du modèle d'embedding choisi
EMBEDDING_DIM = 384
COLLECTION_NAME = settings.milvus_collection

class MilvusService:
    """Service de recherche vectorielle sur la base Wikichess."""

    def __init__(self):
        self._model: SentenceTransformer | None = None
        self._collection: Collection | None = None
        self._connected: bool = False

    # -
    # Connexion & initialisation
    # -

    def connect(self):
        """Établit la connexion à Milvus Standalone."""
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
        self._connected = True
        logger.info(f"Connecté à Milvus sur {settings.milvus_host}:{settings.milvus_port}")

    def _ensure_connected(self):
        """Établit la connexion si ce n'est pas déjà fait (lazy connect)."""
        if not self._connected:
            self.connect()

    def get_model(self) -> SentenceTransformer:
        """Charge le modèle d'embedding (lazy loading)."""
        if self._model is None:
            logger.info("Chargement du modèle d'embedding all-MiniLM-L6-v2...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def get_collection(self) -> Collection:
        """Retourne la collection Milvus (la crée si elle n'existe pas)."""
        self._ensure_connected()
        if not utility.has_collection(COLLECTION_NAME):
            self._create_collection()
        if self._collection is None:
            self._collection = Collection(COLLECTION_NAME)
            self._collection.load()
        return self._collection

    # -
    # Création du schéma de collection
    # -

    def _create_collection(self):
        """Crée le schéma de la collection chess_openings dans Milvus."""
        fields = [
            FieldSchema(name="id",           dtype=DataType.INT64,         is_primary=True, auto_id=True),
            FieldSchema(name="opening_name", dtype=DataType.VARCHAR,        max_length=256),
            FieldSchema(name="eco_code",     dtype=DataType.VARCHAR,        max_length=10),
            FieldSchema(name="chunk_text",   dtype=DataType.VARCHAR,        max_length=4096),
            FieldSchema(name="source_url",   dtype=DataType.VARCHAR,        max_length=512),
            FieldSchema(name="embedding",    dtype=DataType.FLOAT_VECTOR,  dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields=fields, description="Wikichess - ouvertures aux échecs")
        collection = Collection(name=COLLECTION_NAME, schema=schema)

        # Index HNSW pour la recherche ANN
        index_params = {
            "metric_type": "COSINE",
            "index_type":  "HNSW",
            "params":      {"M": 16, "efConstruction": 200},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        # Index scalaire sur eco_code pour permettre le filtrage et la suppression
        collection.create_index(field_name="eco_code", index_params={"index_type": "Trie"})
        collection.load()
        self._collection = collection
        logger.info(f"Collection '{COLLECTION_NAME}' créée avec index HNSW.")

    # -
    # Déduplication
    # -

    def delete_by_eco_codes(self, eco_codes: list[str]) -> None:
        """Supprime les entrées existantes pour les codes ECO donnés (upsert côté Milvus)."""
        if not eco_codes:
            return
        collection = self.get_collection()
        codes_str = ", ".join(f'"{c}"' for c in eco_codes)
        expr = f"eco_code in [{codes_str}]"
        collection.delete(expr=expr)
        collection.flush()
        logger.info(f"Entrées existantes supprimées pour {len(eco_codes)} codes ECO.")

    # -
    # Insertion
    # -

    def insert(self, documents: list[dict]) -> int:
        """
        Insère des documents dans Milvus.

        Chaque document doit avoir :
        - opening_name (str)
        - eco_code     (str)
        - chunk_text   (str)
        - source_url   (str)
        """
        model = self.get_model()
        collection = self.get_collection()

        # Suppression des doublons avant insertion (comportement upsert)
        eco_codes = list({doc["eco_code"] for doc in documents})
        self.delete_by_eco_codes(eco_codes)

        texts = [doc["chunk_text"] for doc in documents]
        embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True).tolist()

        data = [
            [doc["opening_name"] for doc in documents],
            [doc["eco_code"]     for doc in documents],
            [doc["chunk_text"]   for doc in documents],
            [doc["source_url"]   for doc in documents],
            embeddings,
        ]

        result = collection.insert(data)
        collection.flush()
        logger.info(f"{len(documents)} documents insérés dans Milvus.")
        return result.insert_count

    # -
    # Recherche
    # -

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Recherche sémantique dans Milvus.
        Retourne les top_k chunks les plus proches de la requête.
        Exécuté dans un thread séparé pour ne pas bloquer l'event loop FastAPI.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, top_k)

    def _search_sync(self, query: str, top_k: int) -> list[dict]:
        """Appel synchrone à Milvus (model.encode + collection.search sont bloquants)."""
        model = self.get_model()
        collection = self.get_collection()

        query_embedding = model.encode([query], normalize_embeddings=True).tolist()

        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}

        results = collection.search(
            data=query_embedding,
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["opening_name", "eco_code", "chunk_text", "source_url"],
        )

        formatted = []
        for hits in results:
            for hit in hits:
                formatted.append({
                    "opening_name": hit.entity.get("opening_name"),
                    "eco_code":     hit.entity.get("eco_code"),
                    "chunk_text":   hit.entity.get("chunk_text"),
                    "source_url":   hit.entity.get("source_url"),
                    "score":        round(hit.score, 4),
                })
        return formatted

milvus_service = MilvusService()
