# Projet : FFE Chess Agent - Proof of Concept
# Auteur : Bintou DIOP

import httpx
from app.core.config import settings

class LichessService:
    """Interroge l'API Lichess Explorer pour récupérer les coups théoriques d'une position FEN."""

    BASE_URL = "https://explorer.lichess.ovh/masters"

    async def get_moves(self, fen: str) -> dict:
        """
        Retourne les coups théoriques pour une position FEN.
        Source : base de données des parties de maîtres (Lichess Masters DB).
        """
        params = {
            "fen": fen,
            "moves": 10,        # Nombre max de coups retournés
            "topGames": 5,      # Parties de référence associées
        }

        headers = {"User-Agent": "FFE-Chess-Agent/1.0 (educational project)"}
        if settings.lichess_token:
            headers["Authorization"] = f"Bearer {settings.lichess_token}"
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            try:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                return self._format_response(data)

            except httpx.TimeoutException:
                raise TimeoutError("Lichess API timeout - réessayez dans quelques instants.")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Lichess API error {e.response.status_code}: {e.response.text}")

    def _format_response(self, raw: dict) -> dict:
        """Formate la réponse brute Lichess en structure exploitable par l'agent."""
        moves = []
        for m in raw.get("moves", []):
            total = m.get("white", 0) + m.get("draws", 0) + m.get("black", 0)
            win_rate = round((m.get("white", 0) / total * 100), 1) if total else 0
            moves.append({
                "uci": m.get("uci"),          # ex: "e2e4"
                "san": m.get("san"),          # ex: "e4"
                "total_games": total,
                "white_win_pct": win_rate,
                "draw_pct": round((m.get("draws", 0) / total * 100), 1) if total else 0,
            })

        opening = raw.get("opening")
        return {
            "moves": moves,
            "opening": {
                "eco": opening.get("eco") if opening else None,
                "name": opening.get("name") if opening else None,
            },
            "total_games_in_db": sum(
                m["total_games"] for m in moves
            ),
        }

lichess_service = LichessService()
