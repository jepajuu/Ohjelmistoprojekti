import pygame
import socketio

# Asetukset
WIDTH, HEIGHT = 500, 500
GRID_SIZE = 5
CELL_SIZE = WIDTH // GRID_SIZE

# Värit
WHITE = (0, 0, 0)
BLACK = (255, 255, 255)
RED = (255, 0, 0)

# Pygame alustaminen
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laivanupotus")

# SocketIO-yhteys palvelimeen
sio = socketio.Client()
sio.connect('http://192.168.110.137:5000')

# Pelaajan ampumat koordinaatit
shots = []

@sio.on('shot_fired')
def on_shot_fired(data):
    print(f"Osuma vastaanotettu: {data}")
    shots.append((data['x'], data['y']))

def draw_grid():
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(screen, BLACK, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, BLACK, (0, y), (WIDTH, y))

def draw_shots():
    for shot in shots:
        x, y = shot
        pygame.draw.circle(screen, RED, (x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2), 10)

def main():
    running = True
    while running:
        screen.fill(WHITE)
        draw_grid()
        draw_shots()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                grid_x, grid_y = mx // CELL_SIZE, my // CELL_SIZE
                sio.emit('shoot', {'x': grid_x, 'y': grid_y})  # Lähetä palvelimelle

        pygame.display.flip()

    sio.disconnect()
    pygame.quit()

if __name__ == "__main__":
    main()
