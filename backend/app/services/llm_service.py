"""
llm_service.py
-
Génération d'explications pédagogiques en français via Mistral Large.
Prend en entrée les données structurées (coups Lichess ou analyse Stockfish
+ contexte RAG) et produit une explication en langage naturel.
"""

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un coach d'échecs expert qui aide les joueurs de la
Fédération Française des Échecs (FFE) à progresser.

RÈGLES STRICTES - INTERDICTIONS ABSOLUES :
- Ne mentionne JAMAIS un coup ou une suite de coups qui n'est pas dans la liste fournie (ex: interdit d'écrire "prépare f4", "suivi de b5", "permet Nxe4" si ces coups ne sont pas dans les données).
- Ne mentionne JAMAIS un pourcentage, un nombre de parties ou une statistique qui n'est pas dans les données fournies.
- Ne mentionne JAMAIS une structure de pions, une pièce ou une case qui ne figure pas dans les données fournies.
- Ne mentionne JAMAIS un nom de variante qui n'est pas dans les données fournies.
- Si une information est absente des données, dis : "Les données disponibles ne permettent pas d'aller plus loin."

RÈGLES POSITIVES :
- Commente UNIQUEMENT les coups listés, leurs statistiques fournies et le contexte théorique fourni.
- Réponds en français, en 3 à 5 phrases, adapté à un joueur de club."""

class LLMService:
    """Service de génération d'explications pédagogiques avec Mistral Large."""

    def __init__(self):
        self._client: ChatMistralAI | None = None

    def _get_client(self) -> ChatMistralAI:
        """Lazy init du client Mistral."""
        if self._client is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY manquante dans les variables d'environnement.")
            self._client = ChatMistralAI(
                model="mistral-large-latest",
                api_key=settings.mistral_api_key,
                temperature=0.0,
                max_tokens=400,
            )
        return self._client

    def _build_prompt_lichess(
        self,
        fen: str,
        opening_name: str | None,
        opening_eco: str | None,
        moves: list,
        rag_context: list,
    ) -> str:
        """Construit le prompt pour une position avec coups théoriques."""
        top_moves = ", ".join(
            f"{m.get('san', m.get('uci', '?'))} ({m.get('total_games', 0)} parties, {m.get('white_win_pct', 0)}% blancs)"
            for m in moves[:3]
        )

        context_text = ""
        # Filtre les résultats RAG peu pertinents (score < 0.65) avant injection
        relevant = [c for c in rag_context if c.get("chunk_text") and c.get("score", 0.0) >= 0.65]
        if relevant:
            snippets = [c["chunk_text"][:500] for c in relevant[:3]]
            context_text = "\n\nContexte théorique (source : base vectorielle Milvus) :\n" + "\n".join(f"---\n{s}" for s in snippets)

        if opening_name:
            opening_info = f"{opening_eco} - {opening_name}" if opening_eco else opening_name
            opening_line = f"Ouverture : {opening_info}\n"
        else:
            # Pas de nom d'ouverture dans les données -> interdit au LLM d'en inventer un
            opening_line = "Ouverture : non identifiée dans les données (NE PAS nommer l'ouverture).\n"

        return (
            f"Position FEN : {fen}\n"
            f"{opening_line}"
            f"Meilleurs coups des maîtres : {top_moves}"
            f"{context_text}\n\n"
            "Explique brièvement les idées stratégiques de cette position et "
            "pourquoi ces coups sont recommandés."
        )

    def _build_prompt_stockfish(
        self,
        fen: str,
        analysis: list,
    ) -> str:
        """Construit le prompt pour une position analysée par Stockfish."""
        if not analysis:
            return (
                f"Position FEN : {fen}\n\n"
                "Stockfish n'a pas pu analyser cette position. "
                "Indique que les données sont insuffisantes pour commenter."
            )

        best = analysis[0]
        lines = []
        for i, pv in enumerate(analysis[:3]):
            move = pv.get("best_move_san") or pv.get("best_move_uci", "?")
            score = pv.get("score_display", "")
            lines.append(f"  {i+1}. {move} ({score})")

        return (
            f"Position FEN : {fen}\n"
            f"Position hors théorie. Analyse Stockfish profondeur {best.get('depth', 15)} :\n"
            + "\n".join(lines)
            + "\n\n"
            "En te basant UNIQUEMENT sur ces coups et scores fournis par Stockfish, "
            "explique brièvement pourquoi le premier coup est recommandé. "
            "Ne mentionne aucun coup qui n'est pas dans cette liste. "
            "Rappel : 100 centipawns = 1 pion d'avantage (ex: +578 cp = +5.78 pions)."
        )

    async def explain(
        self,
        fen: str,
        source: str,
        opening_name: str | None = None,
        opening_eco: str | None = None,
        moves: list | None = None,
        stockfish_analysis: list | None = None,
        rag_context: list | None = None,
    ) -> str:
        """
        Génère une explication pédagogique en français pour la position.
        Retourne une chaîne vide en cas d'erreur pour ne pas bloquer la réponse.
        """
        try:
            client = self._get_client()

            if source == "lichess":
                prompt = self._build_prompt_lichess(
                    fen=fen,
                    opening_name=opening_name,
                    opening_eco=opening_eco,
                    moves=moves or [],
                    rag_context=rag_context or [],
                )
            else:
                prompt = self._build_prompt_stockfish(
                    fen=fen,
                    analysis=stockfish_analysis or [],
                )

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]

            response = await client.ainvoke(messages)
            content = response.content
            return content.strip() if isinstance(content, str) else str(content).strip()

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Erreur LLM Mistral : {e}")
            return ""

llm_service = LLMService()
