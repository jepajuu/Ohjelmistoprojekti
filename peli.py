import pygame
import sys
import socket
import threading

# Asetukset
WIDTH, HEIGHT = 1200, 800
GRID_SIZE = 10
CELL_SIZE = 50
BOARD_GAP = CELL_SIZE * 2  # Lisää väliä lautojen väliin
LETTERS = "ABCDEFGHIJ"
LIGHT_MODE = {'BG': (255, 255, 255), 'TEXT': (0, 0, 0), 'BUTTON': (200, 200, 200)}
DARK_MODE = {'BG': (30, 30, 30), 'TEXT': (255, 255, 255), 'BUTTON': (70, 70, 70)}
current_mode = DARK_MODE  # Dark mode on nyt oletuksena

toggle_rect = pygame.Rect(1100, 20, 60, 30)

# Laivat
ships = [
    ("Lentotukialus", 5),
    ("Taistelulaiva", 4),
    ("Risteilijä 1", 3),
    ("Risteilijä 2", 3),
    ("Hävittäjä", 2),
    ("Sukellusvene", 1)
]

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laivanupotus")

font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 28)

def draw_text(text, x, y, color, font=font):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def draw_toggle():
    pygame.draw.rect(screen, current_mode['BUTTON'], toggle_rect)
    draw_text("Dark" if current_mode == DARK_MODE else "Light", 1110, 25, current_mode['TEXT'], small_font)

def draw_grid(x_offset, y_offset, board, show_ships=True):
    for row in range(GRID_SIZE):
        draw_text(str(row + 1), x_offset - 30, y_offset + row * CELL_SIZE + 15, current_mode['TEXT'])
        for col in range(GRID_SIZE):
            if row == 0:
                draw_text(LETTERS[col], x_offset + col * CELL_SIZE + 15, y_offset - 30, current_mode['TEXT'])
            rect = pygame.Rect(x_offset + col * CELL_SIZE, y_offset + row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, current_mode['TEXT'], rect, 1)
            if show_ships and board[row][col] == 1:
                pygame.draw.rect(screen, (0, 255, 0), rect)

def place_ships():
    return [[0] * GRID_SIZE for _ in range(GRID_SIZE)]

def input_box():
    user_text = ""
    input_active = True
    while input_active:
        screen.fill(current_mode['BG'])
        draw_text("Syötä palvelimen IP:", 400, 300, current_mode['TEXT'])
        pygame.draw.rect(screen, current_mode['TEXT'], (400, 350, 300, 40), 2)
        text_surface = font.render(user_text, True, current_mode['TEXT'])
        screen.blit(text_surface, (410, 360))
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return user_text
                elif event.key == pygame.K_BACKSPACE:
                    user_text = user_text[:-1]
                else:
                    user_text += event.unicode

def show_game(player_board, opponent_board, connection):
    running = True
    while running:
        screen.fill(current_mode['BG'])
        draw_text("Oma kenttä", 200, 50, current_mode['TEXT'])
        draw_text("Vastustajan kenttä", 700, 50, current_mode['TEXT'])
        draw_grid(100, 100, player_board, show_ships=True)
        draw_grid(100 + GRID_SIZE * CELL_SIZE + BOARD_GAP, 100, opponent_board, show_ships=False)
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

def show_menu():
    global current_mode
    running = True
    while running:
        screen.fill(current_mode['BG'])
        draw_text("Laivanupotus", 400, 100, current_mode['TEXT'], font)
        pygame.draw.rect(screen, current_mode['BUTTON'], (400, 200, 200, 50))
        pygame.draw.rect(screen, current_mode['BUTTON'], (400, 300, 200, 50))
        draw_text("Host", 460, 215, current_mode['TEXT'], small_font)
        draw_text("Join", 460, 315, current_mode['TEXT'], small_font)
        draw_toggle()
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if toggle_rect.collidepoint(mx, my):
                    current_mode = DARK_MODE if current_mode == LIGHT_MODE else LIGHT_MODE
                elif 400 <= mx <= 600 and 200 <= my <= 250:
                    player_board = place_ships()
                    opponent_board = place_ships()
                    show_game(player_board, opponent_board, None)
                elif 400 <= mx <= 600 and 300 <= my <= 350:
                    ip = input_box()
                    player_board = place_ships()
                    opponent_board = place_ships()
                    show_game(player_board, opponent_board, None)

if __name__ == "__main__":
    show_menu()
