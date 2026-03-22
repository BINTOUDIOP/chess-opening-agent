# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

import chess
import chess.engine
import asyncio
from app.core.config import settings

class StockfishService:
    """
    Encapsule les appels à Stockfish pour l'évaluation de positions FEN.
    Utilise une instance de moteur persistante (singleton async) pour éviter
    de relancer le processus à chaque requête.
    """

    def __init__(self):
        self.engine_path = settings.stockfish_path
        self.depth = settings.stockfish_depth
        self._engine: chess.engine.Protocol | None = None
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _validate_fen(self, fen: str) -> chess.Board:
        try:
            return chess.Board(fen)
        except ValueError:
            raise ValueError(f"FEN invalide : '{fen}'")

    async def _get_engine(self) -> chess.engine.Protocol:
        """Retourne l'instance du moteur, en la créant si nécessaire."""
        async with self._get_lock():
            if self._engine is None:
                try:
                    _, self._engine = await chess.engine.popen_uci(self.engine_path)
                except FileNotFoundError:
                    raise RuntimeError(
                        f"Stockfish introuvable à '{self.engine_path}'. "
                        "Vérifiez que le binaire est bien installé dans le conteneur."
                    )
        return self._engine

    async def evaluate(self, fen: str) -> dict:
        """
        Évalue une position FEN avec Stockfish.
        Retourne le score en centipawns, le meilleur coup et une ligne principale (PV).
        Timeout : 10 secondes.
        """
        board = self._validate_fen(fen)
        try:
            engine = await self._get_engine()
            info = await engine.analyse(
                board,
                chess.engine.Limit(depth=self.depth, time=10.0),
                multipv=3,
            )
        except Exception:
            self._engine = None  # reset pour la prochaine requête
            raise

        results = []
        for pv_info in info if isinstance(info, list) else [info]:
            raw_score = pv_info.get("score")
            if raw_score is None:
                continue
            score = raw_score.white()
            pv_moves = pv_info.get("pv", [])

            if score.is_mate():
                score_str = f"Mat en {score.mate()}"
                score_cp = None
            else:
                score_cp = score.score()
                score_str = f"{score_cp:+d} cp"

            best_move_san = None
            if pv_moves:
                try:
                    best_move_san = board.san(pv_moves[0])
                except Exception:
                    best_move_san = pv_moves[0].uci()

            results.append({
                "best_move_uci": pv_moves[0].uci() if pv_moves else None,
                "best_move_san": best_move_san,
                "score_cp": score_cp,
                "score_display": score_str,
                "pv_uci": [m.uci() for m in pv_moves[:5]],
                "depth": pv_info.get("depth", self.depth),
            })

        if not results:
            raise RuntimeError("Stockfish n'a retourné aucun résultat pour cette position.")

        return {
            "fen": board.fen(),
            "turn": "white" if board.turn == chess.WHITE else "black",
            "analysis": results,
            "source": "stockfish",
        }

    async def get_best_move(self, fen: str) -> dict:
        """Retourne uniquement le meilleur coup (usage simplifié par LangGraph)."""
        analysis = await self.evaluate(fen)
        best = analysis["analysis"][0] if analysis["analysis"] else {}
        return {
            "fen": fen,
            "best_move_uci": best.get("best_move_uci"),
            "best_move_san": best.get("best_move_san"),
            "score_cp": best.get("score_cp"),
            "score_display": best.get("score_display"),
        }

stockfish_service = StockfishService()
