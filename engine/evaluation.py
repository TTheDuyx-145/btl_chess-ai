"""
Hàm đánh giá vị trí cờ vua (Position Evaluation)

Trả về điểm từ góc nhìn của bên đang đi (negamax convention):
  > 0 : có lợi cho bên đang đi
  < 0 : bất lợi cho bên đang đi
"""

import chess

# ─── Giá trị quân cờ (centipawn) ──────────────────────────────────────────────
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

CHECKMATE_SCORE = 30_000

# ─── Piece-Square Tables (PST) ─────────────────────────────────────────────────
# Định nghĩa từ góc nhìn của Trắng: hàng 0 = hàng 8, hàng 7 = hàng 1
# Cột 0 = cột a, cột 7 = cột h
#
# Cách dùng:
#   Trắng tại ô s: index = (7 - rank(s)) * 8 + file(s)
#   Đen  tại ô s: index = rank(s) * 8 + file(s)  (lật dọc)

PAWN_PST = [
     0,   0,   0,   0,   0,   0,   0,   0,  # hàng 8
    50,  50,  50,  50,  50,  50,  50,  50,  # hàng 7
    10,  10,  20,  30,  30,  20,  10,  10,  # hàng 6
     5,   5,  10,  25,  25,  10,   5,   5,  # hàng 5
     0,   0,   0,  20,  20,   0,   0,   0,  # hàng 4
     5,  -5, -10,   0,   0, -10,  -5,   5,  # hàng 3
     5,  10,  10, -20, -20,  10,  10,   5,  # hàng 2
     0,   0,   0,   0,   0,   0,   0,   0,  # hàng 1
]

KNIGHT_PST = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_PST = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_PST = [
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0,
]

QUEEN_PST = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
]

# Vua: khác nhau giữa trung cuộc và tàn cuộc
KING_MIDGAME_PST = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20,
]

KING_ENDGAME_PST = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]

PST_MAP = {
    chess.PAWN:   PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK:   ROOK_PST,
    chess.QUEEN:  QUEEN_PST,
}


def _pst_index(square: int, is_white: bool) -> int:
    rank = chess.square_rank(square)   # 0 = hàng 1, 7 = hàng 8
    file = chess.square_file(square)   # 0 = cột a, 7 = cột h
    row = (7 - rank) if is_white else rank
    return row * 8 + file


def _pst_value(piece_type: int, square: int, is_white: bool, endgame: bool) -> int:
    if piece_type == chess.KING:
        table = KING_ENDGAME_PST if endgame else KING_MIDGAME_PST
    else:
        table = PST_MAP[piece_type]
    return table[_pst_index(square, is_white)]


def _is_endgame(board: chess.Board) -> bool:
    """Tàn cuộc khi không còn hậu, hoặc mỗi bên còn ít quân."""
    if not board.queens:
        return True
    white_minor = (
        len(board.pieces(chess.ROOK,   chess.WHITE)) * 500 +
        len(board.pieces(chess.BISHOP, chess.WHITE)) * 330 +
        len(board.pieces(chess.KNIGHT, chess.WHITE)) * 320
    )
    black_minor = (
        len(board.pieces(chess.ROOK,   chess.BLACK)) * 500 +
        len(board.pieces(chess.BISHOP, chess.BLACK)) * 330 +
        len(board.pieces(chess.KNIGHT, chess.BLACK)) * 320
    )
    return white_minor <= 1300 and black_minor <= 1300


def _pawn_structure(board: chess.Board) -> int:
    """
    Đánh giá cấu trúc tốt:
      - Tốt chồng (doubled pawn): -15
      - Tốt cô lập (isolated pawn): -20
      - Tốt thông (passed pawn): +20 .. +90 tuỳ mức tiến
    Trả về điểm từ góc nhìn Trắng.
    """
    score = 0
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        pawns = board.pieces(chess.PAWN, color)
        pawn_files = [chess.square_file(sq) for sq in pawns]

        for sq in pawns:
            f = chess.square_file(sq)

            # Tốt chồng
            if pawn_files.count(f) > 1:
                score -= sign * 15

            # Tốt cô lập
            neighbor = (f > 0 and (f - 1) in pawn_files) or (f < 7 and (f + 1) in pawn_files)
            if not neighbor:
                score -= sign * 20

            # Tốt thông
            if _is_passed_pawn(board, sq, color):
                rank = chess.square_rank(sq)
                advance = rank if color == chess.WHITE else (7 - rank)
                score += sign * (20 + advance * 10)

    return score


def _is_passed_pawn(board: chess.Board, square: int, color: chess.Color) -> bool:
    """Tốt thông: không có tốt đối phương cản phía trước (cùng cột hoặc kề)."""
    f = chess.square_file(square)
    r = chess.square_rank(square)
    enemy_pawns = board.pieces(chess.PAWN, not color)

    for ep in enemy_pawns:
        ef = chess.square_file(ep)
        er = chess.square_rank(ep)
        if abs(ef - f) <= 1:
            if color == chess.WHITE and er > r:
                return False
            if color == chess.BLACK and er < r:
                return False
    return True


def _bishop_pair_bonus(board: chess.Board) -> int:
    """Cặp tượng: +50 so với đơn tượng."""
    score = 0
    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += 50
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= 50
    return score


# ─── Hàm đánh giá chính ───────────────────────────────────────────────────────

def evaluate(board: chess.Board) -> int:
    """
    Đánh giá tĩnh vị trí hiện tại.
    Trả về điểm từ góc nhìn của bên đang đến lượt đi (negamax convention).
    """
    if board.is_checkmate():
        return -CHECKMATE_SCORE
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    endgame = _is_endgame(board)
    score = 0  # dương = có lợi cho Trắng

    # Vật chất + vị trí
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        value = PIECE_VALUES[piece.piece_type] + _pst_value(piece.piece_type, sq, piece.color, endgame)
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value

    # Cấu trúc tốt
    score += _pawn_structure(board)

    # Cặp tượng
    score += _bishop_pair_bonus(board)

    # Trả về theo góc nhìn của bên đang đi
    return score if board.turn == chess.WHITE else -score
