"""
UCI (Universal Chess Interface) – giao tiếp với GUI cờ vua bên ngoài
(Arena, Lichess, cutechess, v.v.)

Chạy: python uci.py
"""

import sys
import chess
from engine import ChessEngine

NAME    = "ChessBot-Minimax"
AUTHOR  = "SinhVien"


def uci_loop() -> None:
    board  = chess.Board()
    engine = ChessEngine(max_depth=3, time_limit=5.0)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        tokens = line.split()
        cmd    = tokens[0]

        # ── Nhận dạng engine ──
        if cmd == "uci":
            print(f"id name {NAME}")
            print(f"id author {AUTHOR}")
            print("option name Depth type spin default 3 min 1 max 10")
            print("option name MoveTime type spin default 5000 min 100 max 60000")
            print("uciok", flush=True)

        elif cmd == "isready":
            print("readyok", flush=True)

        elif cmd == "ucinewgame":
            board  = chess.Board()
            engine = ChessEngine(max_depth=engine.max_depth,
                                 time_limit=engine.time_limit)

        # ── Thiết lập vị trí ──
        elif cmd == "position":
            board = _parse_position(tokens)

        # ── Tìm nước đi ──
        elif cmd == "go":
            params = _parse_go(tokens)
            _apply_go_options(engine, params)

            move = engine.get_best_move(board)
            if move:
                print(f"bestmove {move.uci()}", flush=True)
            else:
                print("bestmove 0000", flush=True)

        # ── Tuỳ chọn ──
        elif cmd == "setoption":
            _parse_setoption(tokens, engine)

        elif cmd in ("stop", "ponderhit"):
            pass   # chưa hỗ trợ pondering

        elif cmd == "quit":
            break


def _parse_position(tokens: list) -> chess.Board:
    board = chess.Board()

    if len(tokens) < 2:
        return board

    idx = 1
    if tokens[idx] == "startpos":
        idx += 1
    elif tokens[idx] == "fen":
        fen_parts = []
        idx += 1
        while idx < len(tokens) and tokens[idx] != "moves":
            fen_parts.append(tokens[idx])
            idx += 1
        board = chess.Board(" ".join(fen_parts))

    if idx < len(tokens) and tokens[idx] == "moves":
        idx += 1
        for uci_move in tokens[idx:]:
            move = chess.Move.from_uci(uci_move)
            # Tự động xử lý phong hậu
            if board.piece_at(move.from_square) and \
               board.piece_at(move.from_square).piece_type == chess.PAWN and \
               chess.square_rank(move.to_square) in (0, 7) and \
               not move.promotion:
                move = chess.Move(move.from_square, move.to_square, chess.QUEEN)
            board.push(move)

    return board


def _parse_go(tokens: list) -> dict:
    params = {}
    i = 1
    while i < len(tokens):
        key = tokens[i]
        if key in ("movetime", "depth", "wtime", "btime", "winc", "binc", "movestogo"):
            if i + 1 < len(tokens):
                params[key] = int(tokens[i + 1])
                i += 2
                continue
        i += 1
    return params


def _apply_go_options(engine: ChessEngine, params: dict) -> None:
    if "depth" in params:
        engine.max_depth  = params["depth"]
        engine.time_limit = 9999.0
    elif "movetime" in params:
        engine.time_limit = params["movetime"] / 1000.0
        engine.max_depth  = 99
    else:
        # Mặc định
        engine.max_depth  = 5
        engine.time_limit = 5.0


def _parse_setoption(tokens: list, engine: ChessEngine) -> None:
    try:
        name_idx  = tokens.index("name")  + 1
        value_idx = tokens.index("value") + 1
        name  = tokens[name_idx].lower()
        value = tokens[value_idx]

        if name == "depth":
            engine.max_depth = int(value)
        elif name == "movetime":
            engine.time_limit = int(value) / 1000.0
    except (ValueError, IndexError):
        pass


if __name__ == "__main__":
    uci_loop()
