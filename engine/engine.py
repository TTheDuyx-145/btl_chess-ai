"""
Chess AI Engine
===============
Thuật toán:
  1. Iterative Deepening  – tìm sâu dần, dùng kết quả cũ để sắp xếp nước đi
  2. Negamax Alpha-Beta   – minimax viết gọn theo dạng đối xứng
  3. Quiescence Search    – tiếp tục tìm sau khi đạt depth=0 (chỉ xét ăn quân)
  4. Move Ordering        – MVV-LVA, Killer Moves, History Heuristic
  5. Transposition Table  – lưu cache kết quả đã tính
"""

import chess
import chess.polyglot
import time
from typing import Optional

from .evaluation import evaluate, CHECKMATE_SCORE, PIECE_VALUES

INF = float("inf")

# Các flag trong transposition table
TT_EXACT = 0   # giá trị chính xác
TT_LOWER = 1   # lower bound (fail-high / beta cutoff)
TT_UPPER = 2   # upper bound (fail-low)


class ChessEngine:
    def __init__(self, max_depth: int = 3, time_limit: float = 5.0):
        self.max_depth  = max_depth
        self.time_limit = time_limit

        # Transposition Table: zobrist_hash -> {score, depth, flag, move}
        self.tt: dict = {}

        # Killer Moves: 2 nước "yên tĩnh" gây beta cutoff tại mỗi ply
        self.killers: list = [[None, None] for _ in range(128)]

        # History Heuristic: (from_sq, to_sq) -> điểm tích lũy
        self.history: dict = {}

        self.nodes    = 0
        self.start_ts = 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Trả về nước đi tốt nhất từ vị trí hiện tại."""
        self.start_ts = time.time()
        self.nodes    = 0
        self.tt       = {}
        self.killers  = [[None, None] for _ in range(128)]
        self.history  = {}

        best_move      = None
        best_score     = -INF
        completed_depth = 0

        # Iterative Deepening: tìm từ depth=1 đến max_depth
        for depth in range(1, self.max_depth + 1):
            if self._time_up():
                break

            move, score = self._root_search(board, depth)

            if move is not None:
                best_move       = move
                best_score      = score
                completed_depth = depth

            # Tìm thấy chiếu hết → dừng sớm
            if abs(score) >= CHECKMATE_SCORE - 200:
                break

        elapsed = time.time() - self.start_ts
        print(f"  depth={completed_depth}  nodes={self.nodes}  "
              f"score={best_score:+d}  time={elapsed:.2f}s")

        return best_move

    # ──────────────────────────────────────────────────────────────────────────
    # Root Search
    # ──────────────────────────────────────────────────────────────────────────

    def _root_search(self, board: chess.Board, depth: int):
        alpha     = -INF
        beta      = INF
        best_move  = None
        best_score = -INF

        moves = self._order_moves(board, list(board.legal_moves), ply=0)

        for move in moves:
            board.push(move)
            score = -self._alpha_beta(board, depth - 1, -beta, -alpha, ply=1)
            board.pop()

            if score > best_score:
                best_score = score
                best_move  = move

            if score > alpha:
                alpha = score

        return best_move, best_score

    # ──────────────────────────────────────────────────────────────────────────
    # Alpha-Beta Negamax
    # ──────────────────────────────────────────────────────────────────────────

    def _alpha_beta(self, board: chess.Board, depth: int,
                    alpha: float, beta: float, ply: int) -> float:
        self.nodes += 1

        # Kiểm tra hết giờ mỗi 2048 node
        if self.nodes & 2047 == 0 and self._time_up():
            return evaluate(board)

        # ── Transposition Table Lookup ──
        tt_key  = chess.polyglot.zobrist_hash(board)
        tt_hit  = self.tt.get(tt_key)
        tt_move = None

        if tt_hit and tt_hit["depth"] >= depth:
            s, flag = tt_hit["score"], tt_hit["flag"]
            if flag == TT_EXACT:
                return s
            if flag == TT_LOWER and s >= beta:
                return s
            if flag == TT_UPPER and s <= alpha:
                return s
            tt_move = tt_hit["move"]

        # ── Kết thúc game ──
        if board.is_game_over():
            if board.is_checkmate():
                return -(CHECKMATE_SCORE - ply)   # bên hiện tại thua
            return 0                               # hòa

        # ── Leaf node → Quiescence Search ──
        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply)

        # ── Duyệt nước đi ──
        original_alpha = alpha
        best_score     = -INF
        best_move      = None

        moves = self._order_moves(board, list(board.legal_moves), ply, tt_move)

        for move in moves:
            board.push(move)
            score = -self._alpha_beta(board, depth - 1, -beta, -alpha, ply + 1)
            board.pop()

            if score > best_score:
                best_score = score
                best_move  = move

            if score > alpha:
                alpha = score

            if alpha >= beta:
                # Beta cutoff
                if not board.is_capture(move):
                    self._store_killer(move, ply)
                    self._update_history(move, depth)
                break

        # ── Lưu vào Transposition Table ──
        if best_score >= beta:
            flag = TT_LOWER
        elif best_score <= original_alpha:
            flag = TT_UPPER
        else:
            flag = TT_EXACT

        self.tt[tt_key] = {
            "score": best_score,
            "depth": depth,
            "flag":  flag,
            "move":  best_move,
        }

        return best_score

    # ──────────────────────────────────────────────────────────────────────────
    # Quiescence Search
    # ──────────────────────────────────────────────────────────────────────────

    def _quiescence(self, board: chess.Board,
                    alpha: float, beta: float, ply: int) -> float:
        """
        Tiếp tục tìm sau depth=0 nhưng chỉ xét các nước ăn quân.
        Tránh "horizon effect": không đánh giá vị trí đang giữa trận đánh.
        """
        self.nodes += 1

        # Điểm "đứng yên" – không đi thêm
        stand_pat = evaluate(board)

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Giới hạn độ sâu quiescence để tránh nổ
        if ply > 30:
            return alpha

        captures = [m for m in board.legal_moves if board.is_capture(m)]
        captures = self._order_captures(board, captures)

        for move in captures:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, ply + 1)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    # ──────────────────────────────────────────────────────────────────────────
    # Move Ordering
    # ──────────────────────────────────────────────────────────────────────────

    def _order_moves(self, board: chess.Board, moves: list,
                     ply: int, tt_move: Optional[chess.Move] = None) -> list:
        """
        Sắp xếp nước đi để alpha-beta cắt tỉa hiệu quả hơn:
          1. Nước TT (từ lần tìm trước)
          2. Ăn quân (MVV-LVA: quân bị ăn giá trị cao, quân ăn giá trị thấp)
          3. Phong hậu
          4. Killer moves
          5. History heuristic
        """
        scored = []
        for move in moves:
            score = 0

            if move == tt_move:
                score = 200_000

            elif board.is_capture(move):
                score = 100_000 + self._mvv_lva(board, move)

            elif move.promotion and move.promotion == chess.QUEEN:
                score = 90_000

            elif move == self.killers[ply][0]:
                score = 80_000
            elif move == self.killers[ply][1]:
                score = 70_000

            else:
                score = self.history.get((move.from_square, move.to_square), 0)

            scored.append((score, move))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _order_captures(self, board: chess.Board, captures: list) -> list:
        """Sắp xếp riêng cho quiescence search."""
        scored = [(self._mvv_lva(board, m), m) for m in captures]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _mvv_lva(self, board: chess.Board, move: chess.Move) -> int:
        """
        MVV-LVA (Most Valuable Victim – Least Valuable Attacker).
        Ưu tiên ăn quân đắt nhất bằng quân rẻ nhất.
        """
        victim   = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)

        victim_val   = PIECE_VALUES.get(victim.piece_type,   0) if victim   else 0
        attacker_val = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0

        # Hệ số 10 để giá trị nạn nhân luôn ưu tiên hơn giá trị kẻ tấn công
        return victim_val * 10 - attacker_val

    # ──────────────────────────────────────────────────────────────────────────
    # Killer & History
    # ──────────────────────────────────────────────────────────────────────────

    def _store_killer(self, move: chess.Move, ply: int) -> None:
        if ply >= 128:
            return
        if move != self.killers[ply][0]:
            self.killers[ply][1] = self.killers[ply][0]
            self.killers[ply][0] = move

    def _update_history(self, move: chess.Move, depth: int) -> None:
        key = (move.from_square, move.to_square)
        self.history[key] = self.history.get(key, 0) + depth * depth

    # ──────────────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────────────

    def _time_up(self) -> bool:
        return (time.time() - self.start_ts) >= self.time_limit
