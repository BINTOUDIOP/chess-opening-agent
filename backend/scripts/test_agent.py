# Projet : FFE Chess Agent, Proof of Concept
# Copyright (c) 2026 Bintou DIOP.

"""
test_agent.py
-------------
Script de test automatique de l'agent IA.
Evalue les 5 scenarios de DEMO_SCENARIOS.md et produit un rapport de qualite.

Usage :
  python scripts/test_agent.py
  python scripts/test_agent.py --url http://localhost:8000
"""

import httpx
import time
import argparse

BASE_URL = "http://localhost:8000"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

SCENARIOS = [
    {
        "id": 1,
        "nom": "Partie du Roi (1.e4)",
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "source_attendue": "lichess",
        "eco_attendu": "B00",
        "min_coups": 5,
        "rag_attendu": True,
        "videos_attendues": True,
    },
    {
        "id": 2,
        "nom": "Sicilienne Najdorf (B90)",
        "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 7",
        "source_attendue": "lichess",
        "eco_attendu": "B90",
        "min_coups": 3,
        "rag_attendu": True,
        "videos_attendues": True,
    },
    {
        "id": 3,
        "nom": "Ruy Lopez (C60)",
        "fen": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        "source_attendue": "lichess",
        "eco_attendu": "C60",
        "min_coups": 3,
        "rag_attendu": True,
        "videos_attendues": True,
    },
    {
        "id": 4,
        "nom": "Defense Francaise (C00)",
        "fen": "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3",
        "source_attendue": "lichess",
        "eco_attendu": "C00",
        "min_coups": 3,
        "rag_attendu": True,
        "videos_attendues": True,
    },
    {
        "id": 5,
        "nom": "Position hors theorie (Stockfish)",
        "fen": "r4rk1/pp2ppbp/2np1np1/q1p5/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9",
        "source_attendue": "stockfish",
        "eco_attendu": None,
        "min_coups": 0,
        "rag_attendu": False,
        "videos_attendues": True,
    },
]


def ok(msg):   return f"{GREEN}OK{RESET}  {msg}"
def fail(msg): return f"{RED}FAIL{RESET} {msg}"
def warn(msg): return f"{YELLOW}WARN{RESET} {msg}"


def evaluer_reponse(scenario: dict, data: dict, duree: float) -> dict:
    resultats = []
    score = 0
    total = 0

    # 1. Source correcte
    total += 1
    source = data.get("source", "")
    if source == scenario["source_attendue"]:
        resultats.append(ok(f"Source = {source}"))
        score += 1
    else:
        resultats.append(fail(f"Source = {source} (attendu : {scenario['source_attendue']})"))

    # 2. Code ECO correct (si lichess)
    if scenario["eco_attendu"]:
        total += 1
        eco = (data.get("opening") or {}).get("eco", "")
        if eco == scenario["eco_attendu"]:
            resultats.append(ok(f"ECO = {eco}"))
            score += 1
        else:
            resultats.append(fail(f"ECO = '{eco}' (attendu : {scenario['eco_attendu']})"))

    # 3. Coups retournes
    if scenario["min_coups"] > 0:
        total += 1
        moves = data.get("moves", [])
        nb = len(moves)
        if nb >= scenario["min_coups"]:
            resultats.append(ok(f"{nb} coups retournes (min attendu : {scenario['min_coups']})"))
            score += 1
        else:
            resultats.append(fail(f"{nb} coups retournes (min attendu : {scenario['min_coups']})"))

    # 4. Explication non vide et sans hallucination evidente
    total += 1
    explication = data.get("explanation", "")
    if explication and len(explication) > 50:
        resultats.append(ok(f"Explication generee ({len(explication)} caracteres)"))
        score += 1
    elif explication:
        resultats.append(warn(f"Explication trop courte ({len(explication)} caracteres)"))
        score += 0.5
    else:
        resultats.append(fail("Explication vide"))

    # 5. Contexte RAG
    if scenario["rag_attendu"]:
        total += 1
        rag = data.get("vector_context", [])
        if rag and len(rag) > 0:
            resultats.append(ok(f"RAG : {len(rag)} chunk(s) retourne(s)"))
            score += 1
        else:
            resultats.append(warn("RAG : aucun chunk (ouverture peut-etre inconnue de Milvus)"))
            score += 0.5

    # 6. Videos YouTube
    if scenario["videos_attendues"]:
        total += 1
        videos = data.get("videos", [])
        if videos and len(videos) > 0:
            resultats.append(ok(f"Videos : {len(videos)} video(s) trouvee(s)"))
            score += 1
        else:
            resultats.append(warn("Videos : aucune video retournee"))
            score += 0.5

    # 7. Temps de reponse
    total += 1
    if duree < 10:
        resultats.append(ok(f"Temps de reponse : {duree:.1f}s"))
        score += 1
    elif duree < 30:
        resultats.append(warn(f"Temps de reponse lent : {duree:.1f}s"))
        score += 0.5
    else:
        resultats.append(fail(f"Temps de reponse trop lent : {duree:.1f}s"))

    # 8. Stockfish : score present si hors theorie
    if scenario["source_attendue"] == "stockfish":
        total += 1
        analysis = data.get("analysis", [])
        if analysis and analysis[0].get("score_display"):
            resultats.append(ok(f"Score Stockfish : {analysis[0]['score_display']}"))
            score += 1
        else:
            resultats.append(fail("Score Stockfish absent"))

    return {
        "resultats": resultats,
        "score": score,
        "total": total,
        "pct": round(score / total * 100) if total else 0,
    }


def tester_cache(url: str, fen: str) -> float:
    """Teste le cache MongoDB : la 2e requete doit etre plus rapide."""
    t = time.time()
    httpx.post(f"{url}/api/v1/agent", json={"fen": fen}, timeout=60)
    return round(time.time() - t, 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=BASE_URL, help="URL du backend (defaut: http://localhost:8000)")
    args = parser.parse_args()
    url = args.url.rstrip("/")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  FFE Chess Agent - Rapport de qualite{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  Backend : {url}\n")

    score_global = 0
    total_global = 0
    resultats_scenarios = []

    for scenario in SCENARIOS:
        print(f"{BOLD}Scenario {scenario['id']} - {scenario['nom']}{RESET}")
        print(f"  FEN : {scenario['fen'][:50]}...")

        try:
            debut = time.time()
            r = httpx.post(
                f"{url}/api/v1/agent",
                json={"fen": scenario["fen"]},
                timeout=60,
            )
            duree = round(time.time() - debut, 2)

            if r.status_code != 200:
                print(f"  {RED}ERREUR HTTP {r.status_code}{RESET}\n")
                resultats_scenarios.append({"id": scenario["id"], "pct": 0, "erreur": True})
                continue

            data = r.json()
            eval_result = evaluer_reponse(scenario, data, duree)

            for ligne in eval_result["resultats"]:
                print(f"  {ligne}")

            pct = eval_result["pct"]
            couleur = GREEN if pct >= 80 else YELLOW if pct >= 50 else RED
            print(f"  {BOLD}Score : {couleur}{eval_result['score']:.1f}/{eval_result['total']} ({pct}%){RESET}")

            score_global += eval_result["score"]
            total_global += eval_result["total"]
            resultats_scenarios.append({"id": scenario["id"], "pct": pct, "erreur": False})

        except httpx.ConnectError:
            print(f"  {RED}Impossible de contacter le backend. Docker est lance ?{RESET}")
            resultats_scenarios.append({"id": scenario["id"], "pct": 0, "erreur": True})
        except Exception as e:
            print(f"  {RED}Erreur : {e}{RESET}")
            resultats_scenarios.append({"id": scenario["id"], "pct": 0, "erreur": True})

        print()

    # Test du cache
    print(f"{BOLD}Test du cache MongoDB{RESET}")
    fen_cache = SCENARIOS[0]["fen"]
    try:
        duree1 = tester_cache(url, fen_cache)
        duree2 = tester_cache(url, fen_cache)
        if duree2 < duree1 * 0.5:
            print(f"  {ok(f'Cache actif : 1ere requete {duree1}s -> 2e requete {duree2}s')}")
            score_global += 1
        else:
            print(f"  {warn(f'Cache peu efficace : {duree1}s -> {duree2}s')}")
            score_global += 0.5
    except Exception:
        print(f"  {warn('Impossible de tester le cache')}")
    total_global += 1
    print()

    # Rapport final
    pct_global = round(score_global / total_global * 100) if total_global else 0
    couleur = GREEN if pct_global >= 80 else YELLOW if pct_global >= 50 else RED

    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  SCORE GLOBAL : {couleur}{score_global:.1f}/{total_global} ({pct_global}%){RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    print("\n  Resume par scenario :")
    for r in resultats_scenarios:
        if r.get("erreur"):
            statut = f"{RED}ERREUR{RESET}"
        elif r["pct"] >= 80:
            statut = f"{GREEN}{r['pct']}%{RESET}"
        elif r["pct"] >= 50:
            statut = f"{YELLOW}{r['pct']}%{RESET}"
        else:
            statut = f"{RED}{r['pct']}%{RESET}"
        print(f"    Scenario {r['id']} : {statut}")

    print()


if __name__ == "__main__":
    main()
