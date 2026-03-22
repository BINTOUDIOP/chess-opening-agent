// Projet : FFE Chess Agent - Proof of Concept
// Auteur : Bintou DIOP

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';

export interface ChessMove {
  uci:            string;
  san:            string;
  total_games:    number;
  white_win_pct:  number;
  draw_pct:       number;
}

export interface VectorResult {
  opening_name: string;
  eco_code:     string;
  chunk_text:   string;
  source_url:   string;
  score:        number;
}

export interface Video {
  video_id:         string;
  title:            string;
  channel:          string;
  description:      string;
  thumbnail:        string;
  url:              string;
  embed_url:        string;
  view_count:       number;
  trusted_channel:  boolean;
  duration_iso:     string;
  published_at?:    string;
}

export interface StockfishLine {
  best_move_uci: string | null;
  best_move_san: string | null;
  score_cp:      number | null;
  score_display: string;
  pv_uci:        string[];
  depth:         number;
}

export interface AgentResponse {
  source:         'lichess' | 'stockfish';
  fen:            string;
  opening?:       { eco: string; name: string };
  moves?:         ChessMove[];
  best_move_uci?: string;
  best_move_san?: string;
  score_display?: string;
  message?:       string;
  analysis?:      StockfishLine[];
  vector_context: VectorResult[];
  videos:         Video[];
  explanation?:   string;
}

@Injectable({ providedIn: 'root' })
export class ChessApiService {

  private readonly API = '/api/v1';

  constructor(private http: HttpClient) {}

  /** Point d'entrée principal : workflow complet de l'agent */
  analyzePosition(fen: string): Observable<AgentResponse> {
    return this.http
      .post<AgentResponse>(`${this.API}/agent`, { fen })
      .pipe(
        timeout(15000),
        catchError(this.handleError),
      );
  }

  /** Coups théoriques uniquement (Lichess) */
  getMoves(fen: string): Observable<any> {
    const encoded = encodeURIComponent(fen);
    return this.http
      .get<any>(`${this.API}/moves/${encoded}`)
      .pipe(catchError(this.handleError));
  }

  /** Évaluation Stockfish uniquement */
  evaluate(fen: string): Observable<any> {
    const encoded = encodeURIComponent(fen);
    return this.http
      .get<any>(`${this.API}/evaluate/${encoded}`)
      .pipe(catchError(this.handleError));
  }

  /** Recherche vectorielle Milvus */
  vectorSearch(query: string, topK = 5): Observable<any> {
    return this.http
      .post<any>(`${this.API}/vector-search`, { query, top_k: topK })
      .pipe(catchError(this.handleError));
  }

  /** Vidéos YouTube pour une ouverture */
  getVideos(opening: string): Observable<any> {
    return this.http
      .get<any>(`${this.API}/videos/${encodeURIComponent(opening)}`)
      .pipe(catchError(this.handleError));
  }

  private handleError(error: HttpErrorResponse) {
    const msg = error.error?.detail ?? error.message ?? 'Erreur réseau inconnue';
    return throwError(() => new Error(msg));
  }
}
