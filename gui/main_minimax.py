"""
Main – Chess GUI dùng Minimax AI (không cần TensorFlow)
Chạy: cd gui && python main_minimax.py
"""

import pygame
import chess

from players import HumanPlayer, MinimaxPlayer
from draw import draw_background, draw_pieces
import globals

pygame.init()

SCREEN_WIDTH  = 700
SCREEN_HEIGHT = 600

win = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Chess – Minimax AI")

board = chess.Board()

# ── Khởi tạo người chơi ──────────────────────────────────────────────────────
# depth=4 đủ cho ~ELO 1200-1400, tăng lên 5 nếu máy mạnh
human     = HumanPlayer(colour="white")
ai_white  = MinimaxPlayer(colour="white", depth=3, time_limit=5.0)
ai_black  = MinimaxPlayer(colour="black", depth=3, time_limit=5.0)

human_white = True          # True: người chơi Trắng, AI chơi Đen
white       = human
black       = ai_black

fps_clock          = pygame.time.Clock()
run                = True
white_move         = True
game_over_countdown = 50


def reset():
	board.reset()
	global white_move
	white_move = True
	globals.from_square = None
	globals.to_square   = None


while run:
	fps_clock.tick(30)

	draw_background(win=win)
	draw_pieces(win=win, fen=board.fen(), human_white=human_white)
	pygame.display.update()

	# ── Kết thúc ván: đếm ngược rồi reset ──────────────────────────────────
	if board.is_game_over():
		result = board.result()
		pygame.display.set_caption(f"Chess – Kết quả: {result}  (reset sau {game_over_countdown} frame)")
		if game_over_countdown > 0:
			game_over_countdown -= 1
		else:
			reset()
			game_over_countdown = 50
			pygame.display.set_caption("Chess – Minimax AI")
		continue

	# ── Lượt AI ─────────────────────────────────────────────────────────────
	if white_move and not human_white:
		white.move(board=board, human_white=human_white)
		white_move = not white_move

	if not white_move and human_white:
		black.move(board=board, human_white=human_white)
		white_move = not white_move

	# ── Xử lý sự kiện ───────────────────────────────────────────────────────
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			run = False
			pygame.quit()

		elif event.type == pygame.MOUSEBUTTONDOWN:
			x, y = pygame.mouse.get_pos()

			# Nút đổi bên (625-675, 200-260)
			if 625 <= x <= 675 and 200 <= y <= 260:
				human_white = not human_white
				if human_white:
					white = human
					white.colour = "white"
					black = ai_black
				else:
					black = human
					black.colour = "black"
					white = ai_white
				reset()

			# Nút reset (630-670, 320-360)
			elif 630 <= x <= 670 and 320 <= y <= 360:
				reset()

		# ── Nước đi của người ───────────────────────────────────────────────
		if white_move and human_white:
			if white.move(board=board, event=event, human_white=human_white):
				white_move = not white_move

		elif not white_move and not human_white:
			if black.move(board=board, event=event, human_white=human_white):
				white_move = not white_move
