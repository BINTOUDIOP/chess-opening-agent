
# Projet : FFE Chess Agent : Proof of Concept
# Auteur : Bintou DIOP

"""
chess_graph.py
-
Workflow LangGraph complet :
  1. validate_fen          :Valide la position FEN
  2. fetch_lichess         :Coups théoriques Lichess
  3. router                :Lichess trouvé -> enrich_context | sinon -> stockfish_fallback
  4a. enrich_context       :RAG Milvus + vidéos YouTube
  4b. stockfish_fallback   -:Analyse Stockfish
  5. generate_explanation  :Explication pédagogique via Mistral Large
  6. build_response        :Réponse finale JSON
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
import logging

from app.services.lichess_service   import lichess_service
from app.services.stockfish_service import stockfish_service
from app.services.milvus_service    import milvus_service
from app.services.youtube_service   import youtube_service
from app.services.llm_service       import llm_service

logger = logging.getLogger(__name__)

class ChessAgentState(TypedDict):
    fen:              str
    is_valid:         bool
    error:            Optional[str]
    lichess_moves:    list
    opening_name:     Optional[str]
    opening_eco:      Optional[str]
    stockfish_result: Optional[dict]
    vector_context:   Optional[list]
    videos:           Optional[list]
    source:           str
    explanation:      Optional[str]
    response:         Optional[dict]

# - Nœuds -

async def validate_fen(state: ChessAgentState) -> ChessAgentState:
    import chess
    try:
        chess.Board(state["fen"])
        state["is_valid"] = True
    except (ValueError, Exception) as e:
        logger.warning(f"FEN invalide : {e}")
        state["is_valid"] = False
        state["error"]    = f"FEN invalide : '{state['fen']}'"
    return state

async def fetch_lichess(state: ChessAgentState) -> ChessAgentState:
    if not state["is_valid"]:
        return state
    try:
        data = await lichess_service.get_moves(state["fen"])
        state["lichess_moves"] = data.get("moves", [])
        opening = data.get("opening") or {}
        state["opening_name"] = opening.get("name")
        state["opening_eco"]  = opening.get("eco")
    except Exception as e:
        logger.error(f"Erreur Lichess : {e}")
        state["error"]         = str(e)
        state["lichess_moves"] = []
    return state

async def stockfish_fallback(state: ChessAgentState) -> ChessAgentState:
    try:
        result = await stockfish_service.evaluate(state["fen"])
        state["stockfish_result"] = result
        state["source"]           = "stockfish"
    except Exception as e:
        logger.error(f"Erreur Stockfish : {e}")
        state["error"] = str(e)
    return state

async def enrich_context(state: ChessAgentState) -> ChessAgentState:
    """RAG Milvus + YouTube en parallèle.

    Le RAG n'est interrogé que si un nom d'ouverture est connu.
    Sans nom d'ouverture, la requête serait trop générique et retournerait
    des chunks hors-sujet qui pourraient induire le LLM en erreur.
    """
    import asyncio

    if state.get("source") != "stockfish":
        state["source"] = "lichess"

    opening_name = state.get("opening_name")

    tasks = []
    if opening_name:
        tasks.append(milvus_service.search(query=opening_name, top_k=3))
    tasks.append(youtube_service.search_videos(opening=opening_name or "chess opening", max_results=4))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    if opening_name:
        rag_result, yt_result = results
        if isinstance(rag_result, Exception):
            logger.error(f"Erreur RAG Milvus : {rag_result}")
            state["vector_context"] = []
        else:
            state["vector_context"] = rag_result
    else:
        # Pas de nom d'ouverture -> pas de RAG pour éviter un contexte hors-sujet
        yt_result = results[0]
        state["vector_context"] = []

    if isinstance(yt_result, Exception):
        logger.error(f"Erreur YouTube : {yt_result}")
        state["videos"] = []
    else:
        state["videos"] = yt_result

    return state

async def generate_explanation(state: ChessAgentState) -> ChessAgentState:
    """Génère une explication pédagogique en français via Mistral Large."""
    if not state.get("is_valid"):
        return state
    try:
        sf_analysis = []
        if state.get("stockfish_result"):
            sf_analysis = state["stockfish_result"].get("analysis", [])

        explanation = await llm_service.explain(
            fen=state["fen"],
            source=state["source"],
            opening_name=state.get("opening_name"),
            opening_eco=state.get("opening_eco"),
            moves=state.get("lichess_moves", []),
            stockfish_analysis=sf_analysis,
            rag_context=state.get("vector_context", []),
        )
        state["explanation"] = explanation
    except Exception as e:
        logger.error(f"Erreur génération explication LLM : {e}")
        state["explanation"] = ""
    return state

async def build_response(state: ChessAgentState) -> ChessAgentState:
    if state.get("error") and not state.get("is_valid"):
        state["response"] = {"error": state["error"]}
        return state

    base = {
        "fen":            state["fen"],
        "vector_context": state.get("vector_context") or [],
        "videos":         state.get("videos") or [],
        "explanation":    state.get("explanation", ""),
    }

    if state["source"] == "lichess":
        state["response"] = {
            **base,
            "source":  "lichess",
            "opening": {"eco": state.get("opening_eco"), "name": state.get("opening_name")},
            "moves":   state["lichess_moves"],
        }
    else:
        sf       = state.get("stockfish_result", {})
        analysis = sf.get("analysis", [{}])
        best     = analysis[0] if analysis else {}
        state["response"] = {
            **base,
            "source":        "stockfish",
            "message":       "Position hors théorie - analyse moteur.",
            "best_move_uci": best.get("best_move_uci"),
            "best_move_san": best.get("best_move_san"),
            "score_display": best.get("score_display"),
            "analysis":      analysis,
        }
    return state

def route_after_lichess(state: ChessAgentState) -> str:
    if not state["is_valid"]:     return "build_response"
    if state["lichess_moves"]:    return "enrich_context"
    return "stockfish_fallback"

def build_chess_graph():
    graph = StateGraph(ChessAgentState)
    graph.add_node("validate_fen",          validate_fen)
    graph.add_node("fetch_lichess",         fetch_lichess)
    graph.add_node("stockfish_fallback",    stockfish_fallback)
    graph.add_node("enrich_context",        enrich_context)
    graph.add_node("generate_explanation",  generate_explanation)
    graph.add_node("build_response",        build_response)
    graph.set_entry_point("validate_fen")
    graph.add_edge("validate_fen", "fetch_lichess")
    graph.add_conditional_edges(
        "fetch_lichess", route_after_lichess,
        {"enrich_context": "enrich_context",
         "stockfish_fallback": "stockfish_fallback",
         "build_response": "build_response"},
    )
    graph.add_edge("enrich_context",       "generate_explanation")
    graph.add_edge("stockfish_fallback",   "enrich_context")
    graph.add_edge("generate_explanation", "build_response")
    graph.add_edge("build_response",       END)
    return graph.compile()

chess_agent = build_chess_graph()
