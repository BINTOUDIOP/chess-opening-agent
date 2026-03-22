// Projet : FFE Chess Agent - Proof of Concept
// Auteur : Bintou DIOP

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChessApiService, AgentResponse } from './services/chess-api.service';
import { TrustUrlPipe } from './pipes/trust-url.pipe';

type Piece = 'K'|'Q'|'R'|'B'|'N'|'P'|'k'|'q'|'r'|'b'|'n'|'p'|'';
const UNICODE: Record<string,string> = {
  K:'♔',Q:'♕',R:'♖',B:'♗',N:'♘',P:'♙',
  k:'♚',q:'♛',r:'♜',b:'♝',n:'♞',p:'♟'
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, TrustUrlPipe],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  board: Piece[][] = [];
  selected: string|null = null;
  highlights: string[] = [];
  currentTurn: 'w'|'b' = 'w';
  currentFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
  castlingRights = 'KQkq';
  halfMoveClock = 0;
  fullMoveNumber = 1;
  moveHistory: string[] = [];
  files = ['a','b','c','d','e','f','g','h'];
  loading = false;
  error = '';
  response: AgentResponse | null = null;
  tab: 'moves'|'context'|'videos' = 'moves';
  activeVideo: any = null;

  constructor(private api: ChessApiService) {}

  ngOnInit() { this.parseFen(this.currentFen); this.analyze(); }

  parseFen(fen: string) {
    const parts = fen.split(' ');
    const position = parts[0] || '';
    const turn = parts[1];
    this.currentTurn = (turn === 'w' || turn === 'b') ? turn : 'w';
    this.castlingRights = parts[2] || '-';
    this.halfMoveClock = parseInt(parts[4] ?? '0', 10) || 0;
    this.fullMoveNumber = parseInt(parts[5] ?? '1', 10) || 1;
    this.board = [];
    for (const row of position.split('/')) {
      const rank: Piece[] = [];
      for (const ch of row) {
        if (isNaN(+ch)) rank.push(ch as Piece);
        else for (let i=0;i<+ch;i++) rank.push('');
      }
      this.board.push(rank);
    }
  }

  onCellClick(r: number, f: number) {
    const key = `${r},${f}`;
    const piece = this.board[r][f];
    if (this.selected) {
      const [sr,sf] = this.selected.split(',').map(Number);
      if (this.selected === key) { this.selected=null; this.highlights=[]; return; }
      this.movePiece(sr,sf,r,f); return;
    }
    if (piece && this.isCurrentPlayer(piece)) {
      this.selected = key;
      this.highlights = this.getLegalMoves(r,f);
    }
  }

  isCurrentPlayer(p: Piece): boolean {
    if (!p) return false;
    return this.currentTurn==='w' ? p===p.toUpperCase() : p===p.toLowerCase();
  }
  isHighlight(r: number, f: number): boolean { return this.highlights.includes(`${r},${f}`); }

  movePiece(sr: number, sf: number, tr: number, tf: number) {
    const piece = this.board[sr][sf];
    const moveUci = `${this.files[sf]}${8-sr}${this.files[tf]}${8-tr}`;
    const captured = this.board[tr][tf];
    const nb = this.board.map(row=>[...row]);
    nb[tr][tf] = piece; nb[sr][sf] = '';
    if (piece==='P'&&tr===0) nb[tr][tf]='Q';
    if (piece==='p'&&tr===7) nb[tr][tf]='q';
    this.board=nb;

    // Mise à jour compteurs FEN
    const isPawnMove = piece === 'P' || piece === 'p';
    const isCapture = captured !== '';
    this.halfMoveClock = (isPawnMove || isCapture) ? 0 : this.halfMoveClock + 1;
    if (this.currentTurn === 'b') this.fullMoveNumber++;

    // Mise à jour des droits de roque
    this.updateCastlingRights(piece, sr, sf);

    this.currentTurn = this.currentTurn==='w'?'b':'w';
    this.moveHistory.push(moveUci);
    this.selected=null; this.highlights=[];
    this.currentFen = this.boardToFen();
    this.analyze();
  }

  private updateCastlingRights(piece: Piece, sr: number, sf: number) {
    let cr = this.castlingRights;
    if (piece === 'K') cr = cr.replace('K','').replace('Q','');
    if (piece === 'k') cr = cr.replace('k','').replace('q','');
    if (piece === 'R') {
      if (sr === 7 && sf === 7) cr = cr.replace('K','');
      if (sr === 7 && sf === 0) cr = cr.replace('Q','');
    }
    if (piece === 'r') {
      if (sr === 0 && sf === 7) cr = cr.replace('k','');
      if (sr === 0 && sf === 0) cr = cr.replace('q','');
    }
    this.castlingRights = cr || '-';
  }

  getLegalMoves(r: number, f: number): string[] {
    const piece = this.board[r][f].toLowerCase();
    const moves: string[] = [];
    const add = (tr:number,tf:number) => {
      if (tr>=0&&tr<8&&tf>=0&&tf<8) {
        const t=this.board[tr][tf];
        if (!t||!this.isCurrentPlayer(t)) moves.push(`${tr},${tf}`);
      }
    };
    const slide = (dr:number,df:number) => {
      let tr=r+dr,tf=f+df;
      while(tr>=0&&tr<8&&tf>=0&&tf<8){
        const t=this.board[tr][tf];
        if(t){if(!this.isCurrentPlayer(t))moves.push(`${tr},${tf}`);break;}
        moves.push(`${tr},${tf}`);tr+=dr;tf+=df;
      }
    };
    if(piece==='p'){const dir=this.currentTurn==='w'?-1:1;const start=this.currentTurn==='w'?6:1;
      if(!this.board[r+dir]?.[f]){add(r+dir,f);if(r===start&&!this.board[r+2*dir]?.[f])add(r+2*dir,f);}
      [-1,1].forEach(df=>{const t=this.board[r+dir]?.[f+df];if(t&&!this.isCurrentPlayer(t))add(r+dir,f+df);});}
    if(piece==='r'||piece==='q')[[1,0],[-1,0],[0,1],[0,-1]].forEach(([dr,df])=>slide(dr,df));
    if(piece==='b'||piece==='q')[[1,1],[1,-1],[-1,1],[-1,-1]].forEach(([dr,df])=>slide(dr,df));
    if(piece==='n')[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]].forEach(([dr,df])=>add(r+dr,f+df));
    if(piece==='k')[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]].forEach(([dr,df])=>add(r+dr,f+df));
    return moves;
  }

  boardToFen(): string {
    const rows = this.board.map(row=>{
      let s='';let e=0;
      for(const p of row){if(p){if(e){s+=e;e=0;}s+=p;}else e++;}
      if(e)s+=e;return s;
    });
    return `${rows.join('/')} ${this.currentTurn} ${this.castlingRights} - ${this.halfMoveClock} ${this.fullMoveNumber}`;
  }

  playSuggestion(uci: string) {
    if(uci.length<4)return;
    const sf=this.files.indexOf(uci[0]),sr=8-parseInt(uci[1]);
    const tf=this.files.indexOf(uci[2]),tr=8-parseInt(uci[3]);
    if(sf<0||sr<0||tf<0||tr<0)return;
    this.movePiece(sr,sf,tr,tf);
  }

  reset() {
    this.currentFen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    this.castlingRights='KQkq'; this.halfMoveClock=0; this.fullMoveNumber=1;
    this.moveHistory=[]; this.activeVideo=null; this.selected=null;
    this.highlights=[]; this.currentTurn='w';
    this.parseFen(this.currentFen); this.analyze();
  }

  playBestMove() {
    if (!this.response || this.loading) return;
    const uci = this.response.source === 'stockfish'
      ? this.response.best_move_uci
      : this.response.moves?.[0]?.uci;
    if (uci) this.playSuggestion(uci);
  }

  analyze() {
    this.loading=true; this.error='';
    this.api.analyzePosition(this.currentFen).subscribe({
      next: r=>{this.response=r;this.loading=false;},
      error: (e: Error)=>{this.error=e.message??'Erreur réseau';this.loading=false;}
    });
  }

  symbol(p: Piece): string { return UNICODE[p]||''; }
  isWhite(p: Piece): boolean { return p===p.toUpperCase(); }
}
