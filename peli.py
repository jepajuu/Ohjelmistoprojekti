import pygame
import sys
import socket
import threading

# Peli-asetukset
WIDTH, HEIGHT = 1200, 800
GRID_SIZE = 10
CELL_SIZE = 50
BOARD_GAP = CELL_SIZE * 2
LETTERS = "ABCDEFGHIJ"
LIGHT_MODE = {'BG': (255, 255, 255), 'TEXT': (0, 0, 0), 'BUTTON': (200, 200, 200)}
DARK_MODE = {'BG': (30, 30, 30), 'TEXT': (255, 255, 255), 'BUTTON': (70, 70, 70)}
current_mode = DARK_MODE

toggle_rect = pygame.Rect(1100, 20, 60, 30)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laivanupotus")

font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 28)

def draw_text(text, x, y, color, font):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def draw_button(text, rect, color, text_color):
    pygame.draw.rect(screen, color, rect)
    draw_text(text, rect.x + 20, rect.y + 10, text_color, font)

def place_ships():
    return [[0] * GRID_SIZE for _ in range(GRID_SIZE)]

def wait_for_opponent():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(1)
    print("Odotetaan vastustajaa...")
    conn, addr = server.accept()
    print(f"Yhdistetty: {addr}")
    return conn

def input_box():
    user_text = ""
    while True:
        screen.fill(current_mode['BG'])
        draw_text("Syötä palvelimen IP:", 400, 300, current_mode['TEXT'], font)
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

def handle_ship_placement(board):
    while True:
        screen.fill(current_mode['BG'])
        draw_text("Sijoita laivasi", 400, 100, current_mode['TEXT'], font)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return board

def show_game(player_board, opponent_board):
    while True:
        screen.fill(current_mode['BG'])
        draw_text("Oma kenttä", 200, 50, current_mode['TEXT'], font)
        draw_text("Vastustajan kenttä", 700, 50, current_mode['TEXT'], font)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

def start_host():
    server_thread = threading.Thread(target=wait_for_opponent, daemon=True)
    server_thread.start()

def show_menu():
    global current_mode
    host_button = pygame.Rect(400, 200, 200, 50)
    join_button = pygame.Rect(400, 300, 200, 50)
    
    while True:
        screen.fill(current_mode['BG'])
        draw_text("Laivanupotus", 400, 100, current_mode['TEXT'], font)
        draw_button("Host", host_button, current_mode['BUTTON'], current_mode['TEXT'])
        draw_button("Join", join_button, current_mode['BUTTON'], current_mode['TEXT'])
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if toggle_rect.collidepoint(mx, my):
                    current_mode = DARK_MODE if current_mode == LIGHT_MODE else LIGHT_MODE
                elif host_button.collidepoint(mx, my):
                    start_host()
                elif join_button.collidepoint(mx, my):
                    ip = input_box()
                    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    connection.connect((ip, 5555))
                    player_board = handle_ship_placement(place_ships())
                    opponent_board = place_ships()
                    show_game(player_board, opponent_board)

if __name__ == "__main__":
    show_menu()
