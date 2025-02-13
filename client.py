import pygame
import sys
import socketio

pygame.init()
pygame.font.init()

LEVEYS, KORKEUS = 800, 600

# Käytetään socket.io-clientiä
sio = socketio.Client()

# Yhdistetään serveriin
SERVER_IP = "127.0.0.1"  # Vaihda palvelimen IP:hen
SERVER_PORT = 5555

def connect_to_server():
    try:
        sio.connect(f"http://{SERVER_IP}:{SERVER_PORT}")
        print("Yhteys palvelimeen onnistui!")
    except Exception as e:
        print("Virhe yhdistettäessä palvelimeen:", e)

@sio.on('player_joined')
def on_player_joined(data):
    print(f"Pelaaja liittyi: {data['ip']}")

@sio.on('player_left')
def on_player_left(data):
    print(f"Pelaaja poistui: {data['ip']}")

@sio.on('receive_message')
def on_receive_message(data):
    print(f"Saapunut viesti: {data['message']}")

def send_message(msg):
    sio.emit('send_message', {"message": msg})

# Pygame UI
fontti = pygame.font.SysFont(None, 24)
screen = pygame.display.set_mode((LEVEYS, KORKEUS))
pygame.display.set_caption("Socket.IO Peli")

def draw_ui():
    screen.fill((30, 30, 30))
    text = fontti.render("Paina ENTER lähettääksesi viestin!", True, (220, 220, 220))
    screen.blit(text, (50, 50))
    pygame.display.flip()

def main():
    connect_to_server()
    clock = pygame.time.Clock()
    running = True

    while running:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    send_message("Pelaaja lähetti viestin!")

        draw_ui()

    sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
