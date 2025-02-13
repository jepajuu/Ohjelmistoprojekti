import pygame
import sys
import socket
import socketio

pygame.init()
pygame.font.init()

LEVEYS, KORKEUS = 800, 600

# Use socket.io-client
sio = socketio.Client()

UDP_DISCOVERY_PORT = 5557  # discovery port for UDP broadcast

def discover_server(timeout=5):
    """
    Broadcasts a UDP discovery message and waits for a server response.
    The server should respond with a known response message.
    """
    discovery_message = b"DISCOVER_SERVER_REQUEST"
    expected_response = "DISCOVER_SERVER_RESPONSE"
    server_ip = None

    # Create UDP socket for broadcast
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(timeout)

    try:
        # Send the discovery message to broadcast address
        udp_sock.sendto(discovery_message, ("<broadcast>", UDP_DISCOVERY_PORT))
        # Wait for the server's response
        data, addr = udp_sock.recvfrom(1024)
        if data.decode() == expected_response:
            server_ip = addr[0]
            print(f"Discovered server at IP: {server_ip}")
        else:
            print("Received unexpected response during discovery.")
    except socket.timeout:
        print("Server discovery timed out.")
    except Exception as e:
        print("Error during discovery:", e)
    finally:
        udp_sock.close()
    return server_ip

def connect_to_server():
    # Try discovery first
    discovered_ip = discover_server()
    if discovered_ip:
        server_ip = discovered_ip
    else:
        # Fallback to manual configuration if discovery fails
        server_ip = input("Enter server IP manually: ")
    SERVER_PORT = 5555
    try:
        sio.connect(f"http://{server_ip}:{SERVER_PORT}")
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