# Projet : FFE Chess Agent - Proof of Concept
# Copyright (c) 2026 Bintou DIOP.

"""
ingest_wikichess.py
-------------------
Script d ingestion entierement automatise.

Sources de donnees officielles :
  1. Dataset ECO officiel Lichess (GitHub lichess-org/chess-openings)
     https://github.com/lichess-org/chess-openings
     Contient 3 000+ ouvertures avec code ECO, nom, coups, FEN

  2. Lichess Masters Opening Explorer
     https://explorer.lichess.ovh/masters
     Retourne les statistiques reelles de parties jouees par des Masters



Usage :
  python scripts/ingest_wikichess.py
"""

import sys
import os
import time
import csv
import io
import json
import argparse
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.milvus_service import milvus_service

# -
# URLs des sources officielles
# -

LICHESS_ECO_URLS = [
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/b.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/c.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/d.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/e.tsv",
]

LICHESS_EXPLORER_URL = "https://explorer.lichess.ovh/masters"

def pgn_to_fen(pgn_str: str) -> str:
    """Génère le FEN final d'une séquence PGN (ex: '1. e4 e5 2. Nf3')."""
    import chess
    import chess.pgn
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if game is None:
            return chess.STARTING_FEN
        return game.end().board().fen()
    except Exception:
        return chess.STARTING_FEN

def fetch_eco_dataset(limit_per_file: int = 100) -> list[dict]:
    """
    Telecharge le dataset ECO officiel depuis GitHub lichess-org/chess-openings.
    Format TSV actuel : eco | name | pgn  (sans colonne fen/uci)
    Le FEN est généré depuis le PGN via la librairie chess.
    """
    all_openings = []
    print("   Telechargement du dataset ECO officiel (lichess-org/chess-openings)...")

    for url in LICHESS_ECO_URLS:
        letter = url.split("/")[-1].replace(".tsv", "").upper()
        try:
            r = httpx.get(url, timeout=15.0)
            r.raise_for_status()
            reader = csv.DictReader(io.StringIO(r.text), delimiter="\t")
            count = 0
            for row in reader:
                if count >= limit_per_file:
                    break
                name = row.get("name", "").strip()
                eco  = row.get("eco", "").strip()
                pgn  = row.get("pgn", "").strip()
                # Colonne fen présente ou générée depuis pgn
                fen  = row.get("fen", "").strip() or (pgn_to_fen(pgn) if pgn else "")
                uci  = row.get("uci", "").strip()
                if eco and name and fen:
                    all_openings.append({
                        "eco":  eco,
                        "name": name,
                        "pgn":  pgn,
                        "uci":  uci,
                        "fen":  fen,
                    })
                    count += 1
            print(f"     ECO {letter} : {count} ouvertures recuperees")
        except Exception as e:
            print(f"     Erreur sur {url} : {e}")

    return all_openings

def fetch_lichess_stats(fen: str) -> dict:
    """
    Recupere les statistiques reelles depuis Lichess Masters Opening Explorer.
    Source : https://explorer.lichess.ovh/masters
    """
    token = os.environ.get("LICHESS_TOKEN", "")
    headers = {"User-Agent": "FFE-Chess-Agent/1.0 (educational project)"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = httpx.get(
            LICHESS_EXPLORER_URL,
            params={"fen": fen, "moves": 5, "topGames": 0},
            headers=headers,
            timeout=10.0
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def build_document(opening: dict, stats: dict) -> dict:
    """
    Construit le document a partir des donnees officielles Lichess.
    Aucune donnee inventee - tout vient des APIs.
    """
    white = stats.get("white", 0)
    draws = stats.get("draws", 0)
    black = stats.get("black", 0)
    total = white + draws + black
    moves = stats.get("moves", [])

    lines = [
        f"Ouverture : {opening['name']} ({opening['eco']})",
        f"Sequence de coups : {opening['pgn']}",
        f"Source ECO : lichess-org/chess-openings (GitHub officiel)",
        f"Source statistiques : Lichess Masters Database",
    ]

    if total > 0:
        pct_white = round(white / total * 100, 1)
        pct_draws = round(draws / total * 100, 1)
        pct_black = round(black / total * 100, 1)
        lines.append(
            f"Statistiques sur {total:,} parties Masters : "
            f"Blancs {pct_white}% - Nulles {pct_draws}% - Noirs {pct_black}%"
        )

    if moves:
        top = []
        for m in moves[:5]:
            mt = m.get("white", 0) + m.get("draws", 0) + m.get("black", 0)
            pct = round(mt / total * 100, 1) if total else 0
            top.append(f"{m.get('san', '')} ({pct}%)")
        lines.append("Coups les plus joues : " + " - ".join(top))

    return {
        "opening_name": opening["name"],
        "eco_code":     opening["eco"],
        "source_url":   f"https://lichess.org/opening/{opening['name'].replace(' ', '_')}",
        "chunk_text":   "\n".join(lines),
    }

CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), ".ingest_checkpoint.json")

def load_checkpoint() -> set:
    """Retourne l'ensemble des ECO déjà ingérés (reprise après interruption)."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return set(json.load(f))
    return set()

def save_checkpoint(done: set) -> None:
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(done), f)

def main():
    parser = argparse.ArgumentParser(description="Ingestion des ouvertures dans Milvus")
    parser.add_argument("--limit", type=int, default=100,
                        help="Nombre max d'ouvertures par fichier ECO (défaut : 100)")
    parser.add_argument("--reset", action="store_true",
                        help="Ignore le checkpoint et réingère tout")
    args = parser.parse_args()

    print("=" * 60)
    print("Ingestion automatique - Sources officielles Lichess")
    print("=" * 60)
    print()

    # 1. Connexion Milvus
    print("1. Connexion a Milvus...")
    milvus_service.connect()
    print("   OK\n")

    # Vider la collection si --reset
    if args.reset:
        from pymilvus import Collection, utility
        if utility.has_collection("chess_openings"):
            col = Collection("chess_openings")
            col.delete(expr="id >= 0")
            col.flush()
            print("   Collection videe (--reset)")
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            print("   Checkpoint efface (--reset)")
        print()

    # 2. Telechargement dataset ECO officiel
    print(f"2. Telechargement dataset ECO officiel (limite : {args.limit}/fichier)...")
    openings = fetch_eco_dataset(limit_per_file=args.limit)
    print(f"   Total : {len(openings)} ouvertures chargees\n")

    # Filtrage via checkpoint
    done_ecos = set() if args.reset else load_checkpoint()
    openings = [o for o in openings if o["eco"] not in done_ecos]
    if done_ecos and not args.reset:
        print(f"   (checkpoint : {len(done_ecos)} déjà ingérées, {len(openings)} restantes)\n")

    if not openings:
        print("Echec du telechargement. Verifiez la connexion internet.")
        sys.exit(1)

    # 3. Enrichissement avec statistiques Lichess Masters
    print("3. Enrichissement avec statistiques Lichess Masters Explorer...")
    documents = []
    for i, opening in enumerate(openings, 1):
        print(f"   [{i}/{len(openings)}] {opening['name']} ({opening['eco']})...")
        stats = fetch_lichess_stats(opening["fen"])
        total = stats.get("white", 0) + stats.get("draws", 0) + stats.get("black", 0)
        if total > 0:
            print(f"          {total:,} parties Masters trouvees")
        else:
            print(f"          Pas de statistiques Masters disponibles")
        doc = build_document(opening, stats)
        documents.append(doc)
        done_ecos.add(opening["eco"])
        save_checkpoint(done_ecos)
        time.sleep(0.8)

    # 4. Insertion dans Milvus
    print(f"\n4. Insertion de {len(documents)} documents dans Milvus...")
    count = milvus_service.insert(documents)
    print(f"\nOK - {count} documents inseres")
    print()
    print("Sources des donnees :")
    print("  ECO dataset : https://github.com/lichess-org/chess-openings")
    print("  Statistiques : https://explorer.lichess.ovh/masters")

if __name__ == "__main__":
    main()
