# Scénarios de démonstration : FFE Chess Agent

---

## Scénario 1 - Ouverture classique : Partie du Roi (1.e4)
**Ce que ça montre** : Lichess trouve 10 coups théoriques avec statistiques Masters, explication pédagogique en français.

**FEN** : `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`

**Situation** : Les Blancs viennent de jouer 1.e4. À toi de choisir la réponse des Noirs.

**Résultat attendu** :
- Source : `lichess`
- Ouverture : King's Pawn Game (B00)
- 10 coups proposés (c5, e5, e6, c6, d6…) avec % victoires
- +1,3 million de parties Masters dans la base

```bash
curl -s -X POST http://localhost:4200/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"}' \
  --max-time 30 | python3 -m json.tool
```

---

## Scénario 2 : Défense Sicilienne Najdorf
**Ce que ça montre** : Une des ouvertures les plus jouées au monde, bien connue de la base Lichess. RAG avec contexte théorique enrichi.

**FEN** : `rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 7`

**Situation** : Après 1.e4 c5 2.Cf3 d6 3.d4 cxd4 4.Cxd4 Cf6 5.Cc3 a6 - position centrale de la Najdorf.

**Résultat attendu** :
- Source : `lichess`
- Ouverture : Sicilian Defense: Najdorf Variation (B90)
- 10 coups des Blancs avec statistiques
- Explication sur les idées stratégiques de la Najdorf

```bash
curl -s -X POST http://localhost:4200/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 7"}' \
  --max-time 30 | python3 -m json.tool
```

---

## Scénario 3 : Ruy Lopez (Partie Espagnole)
**Ce que ça montre** : Ouverture ultra-classique jouée depuis le XVIe siècle, données Masters très riches.

**FEN** : `r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3`

**Situation** : Après 1.e4 e5 2.Cf3 Cc6 3.Fb5 - les Blancs attaquent le défenseur de e5.

**Résultat attendu** :
- Source : `lichess`
- Ouverture : Ruy Lopez (C60)
- Réponses classiques des Noirs (a6 Morphy, Cf6 Berlin, d6…)
- Explication sur la pression exercée sur e5

```bash
curl -s -X POST http://localhost:4200/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"fen": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"}' \
  --max-time 30 | python3 -m json.tool
```

---

## Scénario 4 : Défense Française
**Ce que ça montre** : Ouverture solide et populaire en France - pertinent pour un outil FFE.

**FEN** : `rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3`

**Situation** : Après 1.e4 e6 2.d4 d5 - les Noirs construisent un centre solide.

**Résultat attendu** :
- Source : `lichess`
- Ouverture : French Defense (C00)
- 3 grandes variantes proposées (Advance 3.e5, Exchange 3.exd5, Tarrasch 3.Cd2)
- Explication sur la structure de pions française

```bash
curl -s -X POST http://localhost:4200/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"fen": "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3"}' \
  --max-time 30 | python3 -m json.tool
```

---

## Scénario 5 : Position hors théorie (Stockfish)
**Ce que ça montre** : Quand la position sort de la théorie, l'agent bascule automatiquement sur Stockfish et explique l'analyse moteur.

**FEN** : `r4rk1/pp2ppbp/2np1np1/q1p5/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9`

**Situation** : Milieu de jeu complexe, position inconnue de la base des Masters.

**Résultat attendu** :
- Source : `stockfish`
- Message : "Position hors théorie - analyse moteur"
- 3 meilleures lignes avec score en centipions
- Explication basée sur l'analyse moteur

```bash
curl -s -X POST http://localhost:4200/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"fen": "r4rk1/pp2ppbp/2np1np1/q1p5/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9"}' \
  --max-time 30 | python3 -m json.tool
```

---

## Récapitulatif

| # | Ouverture | ECO | Source attendue | Point clé |
|---|-----------|-----|-----------------|-----------|
| 1 | Partie du Roi (1.e4) | B00 | Lichess | 1,3M parties Masters |
| 2 | Sicilienne Najdorf | B90 | Lichess | Ouverture la plus jouée |
| 3 | Ruy Lopez | C60 | Lichess | Classique historique |
| 4 | Défense Française | C00 | Lichess | Pertinent FFE |
| 5 | Milieu de jeu complexe | - | Stockfish | Fallback moteur |

---

## Test rapide de tous les scénarios

```bash
FENS=(
  "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
  "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 7"
  "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"
  "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3"
  "r4rk1/pp2ppbp/2np1np1/q1p5/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9"
)
for fen in "${FENS[@]}"; do
  echo "--- $fen ---"
  curl -s -X POST http://localhost:4200/api/v1/agent \
    -H "Content-Type: application/json" \
    -d "{\"fen\": \"$fen\"}" --max-time 30 | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print('source:', d.get('source'), '| opening:', d.get('opening',{}).get('name','N/A') if d.get('opening') else 'N/A')"
done
```
