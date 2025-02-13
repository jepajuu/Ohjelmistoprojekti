import pygame
import sys
import socket
import socketio

pygame.init()
pygame.font.init()

LEVEYS, KORKEUS = 800, 600

# Käytetään socket.io-clientia
sio = socketio.Client()

UDP_DISCOVERY_PORT = 5557  # UDP-löytymispalvelu

def discover_server(timeout=5):
    """Etsii palvelimen lähettämällä UDP-broadcastin."""
    discovery_message = b"DISCOVER_SERVER_REQUEST"
    expected_response = "DISCOVER_SERVER_RESPONSE"
    server_ip = None
    
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(timeout)
    
    try:
        udp_sock.sendto(discovery_message, ("<broadcast>", UDP_DISCOVERY_PORT))
        data, addr = udp_sock.recvfrom(1024)
        if data.decode() == expected_response:
            server_ip = addr[0]
            print(f"Palvelin löytyi IP:stä {server_ip}")
    except socket.timeout:
        print("Palvelimen löytyminen aikakatkaistiin.")
    except Exception as e:
        print("Virhe palvelimen etsinnässä:", e)
    finally:
        udp_sock.close()
    
    return server_ip

def connect_to_server():
    discovered_ip = discover_server()
    if discovered_ip:
        server_ip = discovered_ip
    else:
        server_ip = input("Syötä palvelimen IP: ")
    
    SERVER_PORT = 5555
    try:
        sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        print("Yhteys palvelimeen onnistui!")
    except Exception as e:
        print("Virhe yhdistettäessä palvelimeen:", e)

# Pygame UI
fontti = pygame.font.SysFont(None, 50)
screen = pygame.display.set_mode((LEVEYS, KORKEUS))
pygame.display.set_caption("Laivanupotus")

host_rect = pygame.Rect(LEVEYS // 2 - 160, 300, 150, 50)
join_rect = pygame.Rect(LEVEYS // 2 + 10, 300, 150, 50)

def draw_start_screen():
    screen.fill((0, 0, 0))
    otsikko = fontti.render("Laivanupotus peli :D", True, (255, 255, 255))
    pygame.draw.rect(screen, (50, 50, 200), host_rect)
    pygame.draw.rect(screen, (50, 200, 50), join_rect)
    
    host_text = fontti.render("HOST", True, (255, 255, 255))
    join_text = fontti.render("JOIN", True, (255, 255, 255))
    
    screen.blit(otsikko, (LEVEYS // 2 - otsikko.get_width() // 2, 150))
    screen.blit(host_text, (host_rect.x + 35, host_rect.y + 10))
    screen.blit(join_text, (join_rect.x + 35, join_rect.y + 10))
    
    pygame.display.flip()

def main():
    clock = pygame.time.Clock()
    running = True
    start_screen = True
    
    while running:
        clock.tick(30)
        
        if start_screen:
            draw_start_screen()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:  # Host
                        print("Hosting game...")
                        start_screen = False  # Tässä voisi alkaa hostauksen käsittely
                    elif event.key == pygame.K_j:  # Join
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False  # Tässä voisi alkaa liittymisen käsittely
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if host_rect.collidepoint(event.pos):
                        print("Hosting game...")
                        start_screen = False
                    elif join_rect.collidepoint(event.pos):
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False
        else:
            screen.fill((0, 50, 0))
            pygame.display.flip()
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
