import pygame
import sys
import socket
import socketio
import time
import copy
import asyncio

pygame.init()
pygame.font.init()

LEVEYS, KORKEUS = 800, 600

# Käytetään socket.io-clientia
sio = socketio.Client()

UDP_DISCOVERY_PORT = 5557  # UDP-löytymispalvelu

# Synkroninen versio (vanha tapa)
def discover_server_sync(timeout=5):
    """Etsii palvelimen lähettämällä UDP-broadcastin (synkronisesti)."""
    discovery_message = b"DISCOVER_SERVER_REQUEST"
    expected_response = "DISCOVER_SERVER_RESPONSE"
    server_ip = None

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(timeout)

    try:
        udp_sock.sendto(discovery_message, ("<broadcast>", UDP_DISCOVERY_PORT))
        data, addr = udp_sock.recvfrom(1024)
        if data.decode().strip() == expected_response:
            server_ip = addr[0]
            print(f"Palvelin löytyi IP:stä {server_ip}")
    except socket.timeout:
        print("Palvelimen löytyminen aikakatkaistiin.")
    except Exception as e:
        print("Virhe palvelimen etsinnässä:", e)
    finally:
        udp_sock.close()

    return server_ip

# Asynkroninen versio (kolmas vaihtoehto)
class DiscoveryClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_response):
        self.on_response = on_response
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        discovery_message = b"DISCOVER_SERVER_REQUEST"
        self.transport.sendto(discovery_message)

    def datagram_received(self, data, addr):
        message = data.decode().strip()
        if message == "DISCOVER_SERVER_RESPONSE":
            self.on_response(addr[0])
            self.transport.close()

    def error_received(self, exc):
        print("UDP virhe:", exc)

    def connection_lost(self, exc):
        pass

async def discover_server_async(timeout=3):
    """Etsii palvelimen asynkronisesti UDP-broadcastilla."""
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def on_response(ip):
        if not future.done():
            future.set_result(ip)

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DiscoveryClientProtocol(on_response),
        local_addr=("0.0.0.0", 0),
        allow_broadcast=True
    )
    try:
        server_ip = await asyncio.wait_for(future, timeout)
        print(f"Palvelin löytyi asynkronisesti IP:stä {server_ip}")
        return server_ip
    except asyncio.TimeoutError:
        print("Asynkroninen palvelimen etsintä aikakatkaistiin.")
        return None
    finally:
        transport.close()

@sio.on("player_joined")
def on_player_joined(data):
    global players_ready, game_state
    players_ready = data["players_connected"]
    print(f"Pelaajia liittynyt: {players_ready}")

    if players_ready >= 2:
        game_state = "setup_ships"  # vaihtaa laivojen asetus tilaan
        aseta_laivat()

@sio.on("game_start")
def on_game_start(data):
    global game_state
    print(data["message"])  # tulostaa "Peli alkaa"

    game_state = "setup_ships"  # siirtyy laivojen asettamiseen
    print("Pelimuoto setup_ships")

@sio.on('bomb_shot')
def on_bomb_shot(data):
    """
    Vastaanottaa toisen pelaajan ampuman pommin koordinaatit serveriltä.
    """
    x = data.get("x")
    y = data.get("y")
    print(f"Vastustaja ampui ruutuun ({x}, {y})!")
    # Tässä voi käsitellä osumaa/hutia

@sio.on('shot_result')
def on_shot_result(data):
    """
    Vastaanottaa tiedon oman laukauksesi tuloksesta (osuma/huti) serveriltä.
    """
    x = data.get("x")
    y = data.get("y")
    hit = data.get("hit", False)
    print(f"Pommituksen tulos: Ruutu ({x},{y}), osuma: {hit}")
    # Grafiikkaa voidaan lisätä tähän

def connect_to_server():
    # Voit valita halutun etsintämetodin:
    # server_ip = discover_server_sync()
    server_ip = asyncio.run(discover_server_async())
    if not server_ip:
        server_ip = input("Syötä palvelimen IP: ")
    
    SERVER_PORT = 5555
    try:
        sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        print("Yhteys palvelimeen onnistui!")
    except Exception as e:
        print("Virhe yhdistettäessä palvelimeen:", e)

# Pygame UI ja pelilogiikka
fontti = pygame.font.SysFont(None, 50)
screen = pygame.display.set_mode((LEVEYS, KORKEUS))
pygame.display.set_caption("Laivanupotus")

host_rect = pygame.Rect(LEVEYS // 2 - 160, 300, 150, 50)
join_rect = pygame.Rect(LEVEYS // 2 + 5, 300, 150, 50)
laivojen_asetus_rect = pygame.Rect(((LEVEYS // 2) - 150), 400, 300, 50)

# Pelikentän ja laivastojen alustukset
laivat = [[0]*10 for _ in range(10)]
lentotukialus = [[-1, -1], [2, 3], [2, 4], [2, 5], [2, 6]]
lentotukialusCopy = copy.deepcopy(lentotukialus)
taistelulaiva = [[-1, -1], [9, 1], [9, 2], [9, 3]]
taistelulaivaCopy = copy.deepcopy(taistelulaiva)
risteilija1 = [[-1, -1], [1, 2], [1, 3]]
risteilija1Copy = copy.deepcopy(risteilija1)
risteilija2 = [[-1, -1], [1, 6], [2, 6]]
risteilija2Copy = copy.deepcopy(risteilija2)
havittaja = [[-1, -1], [-1, -1]]
havittajaCopy = copy.deepcopy(havittaja)
sukellusvene = [[-1, -1]]
sukellusveneCopy = copy.deepcopy(sukellusvene)

def piirra_ruudukko():
    screen.fill((255, 255, 255))
    for i in range(11):
        pygame.draw.line(screen, (0, 0, 0), [(LEVEYS / 22) * i, 0], [(LEVEYS / 22) * i, KORKEUS])
        pygame.draw.line(screen, (0, 0, 0), [0, (KORKEUS / 11) * i], [LEVEYS / 2, (KORKEUS / 11) * i])
        if i > 0:
            number_text = fontti.render(str(i), True, (0, 0, 0))
            screen.blit(number_text, ((LEVEYS / 22) * 0.1, (KORKEUS / 11) * i + 5))
            aakkonen_text = fontti.render(chr(i + 64), True, (0, 0, 0))
            screen.blit(aakkonen_text, ((LEVEYS / 22) * i + 5, (KORKEUS / 11) * 0.1))
    pygame.display.flip()

def piirra_vihollisen_ruudukko():
    for i in range(11):
        pygame.draw.line(screen, (0, 0, 0), [(LEVEYS / 22) * i + LEVEYS / 2, 0], [(LEVEYS / 22) * i + LEVEYS / 2, KORKEUS])
        pygame.draw.line(screen, (0, 0, 0), [LEVEYS / 2, (KORKEUS / 11) * i], [LEVEYS, (KORKEUS / 11) * i])
        if i > 0:
            number_text = fontti.render(str(i), True, (0, 0, 0))
            screen.blit(number_text, ((LEVEYS / 22) * 0.1 + LEVEYS / 2, (KORKEUS / 11) * i + 5))
            aakkonen_text = fontti.render(chr(i + 64), True, (0, 0, 0))
            screen.blit(aakkonen_text, (((LEVEYS / 22) * i) + 5 + LEVEYS / 2, (KORKEUS / 11) * 0.1))
    pygame.display.flip()

def piirra_laivat():
    global laivat
    # Alustetaan laivat 2D-listaan
    laivat = [[0]*10 for _ in range(10)]
    if lentotukialus[0][0] != -1:
        for coord in lentotukialus:
            laivat[coord[0]][coord[1]] = 1
    if taistelulaiva[0][0] != -1:
        for coord in taistelulaiva:
            laivat[coord[0]][coord[1]] = 1
    if risteilija1[0][0] != -1:
        for coord in risteilija1:
            laivat[coord[0]][coord[1]] = 1
    if risteilija2[0][0] != -1:
        for coord in risteilija2:
            laivat[coord[0]][coord[1]] = 1
    if havittaja[0][0] != -1:
        for coord in havittaja:
            laivat[coord[0]][coord[1]] = 1
    if sukellusvene[0][0] != -1:
        for coord in sukellusvene:
            laivat[coord[0]][coord[1]] = 1

    # Piirretään laivat
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                cell_rect = pygame.Rect((LEVEYS/11)*x + (LEVEYS/11), (KORKEUS/11)*y + (KORKEUS/11), LEVEYS/10.9, KORKEUS/10.9)
                pygame.draw.rect(screen, (50, 50, 200), cell_rect)
    pygame.display.flip()

def aseta_laivat():
    piirra_ruudukko()
    piirra_laivat()
    # Aseta laivat (tässä esimerkkifunktio, jota voidaan kehittää edelleen)
    global taistelulaiva, taistelulaivaCopy
    taistelulaivaCopy = copy.deepcopy(taistelulaiva)
    taistelulaiva[0][0] = -1
    taistelulaiva = aseta_yksi_laiva(taistelulaivaCopy)
    piirra_ruudukko()
    piirra_laivat()

    global lentotukialus, lentotukialusCopy
    lentotukialusCopy = copy.deepcopy(lentotukialus)
    lentotukialus[0][0] = -1
    lentotukialus = aseta_yksi_laiva(lentotukialusCopy)
    piirra_ruudukko()
    piirra_laivat()

    global risteilija1, risteilija1Copy
    risteilija1Copy = copy.deepcopy(risteilija1)
    risteilija1[0][0] = -1
    risteilija1 = aseta_yksi_laiva(risteilija1Copy)
    piirra_ruudukko()
    piirra_laivat()

    global risteilija2, risteilija2Copy
    risteilija2Copy = copy.deepcopy(risteilija2)
    risteilija2[0][0] = -1
    risteilija2 = aseta_yksi_laiva(risteilija2Copy)
    piirra_ruudukko()
    piirra_laivat()

    global havittaja, havittajaCopy
    havittajaCopy = copy.deepcopy(havittaja)
    havittaja[0][0] = -1
    havittaja = aseta_yksi_laiva(havittajaCopy)
    piirra_ruudukko()
    piirra_laivat()

    global sukellusvene, sukellusveneCopy
    sukellusveneCopy = copy.deepcopy(sukellusvene)
    sukellusvene[0][0] = -1
    sukellusvene = aseta_yksi_laiva(sukellusveneCopy)
    piirra_ruudukko()
    piirra_laivat()
    
    pygame.display.flip()
    time.sleep(2)

def piirra_yksi_laiva(laiva_yksi, vari_yksi):
    for coord in laiva_yksi:
        cell_rect = pygame.Rect((LEVEYS/11)*coord[0] + (LEVEYS/11), (KORKEUS/11)*coord[1] + (KORKEUS/11), LEVEYS/10.9, KORKEUS/10.9)
        pygame.draw.rect(screen, (vari_yksi[0], vari_yksi[1], vari_yksi[2]), cell_rect)
    pygame.display.flip()

def aseta_yksi_laiva(laivaTemp):
    vari_asetus = [33, 55, 66]
    if laivaTemp[0][0] == -1:
        for i in range(len(laivaTemp)):
            laivaTemp[i][0] = 0
            laivaTemp[i][1] = i

    piirra_ruudukko()
    piirra_laivat()
    for coord in laivaTemp:
        if laivat[coord[0]][coord[1]]:
            vari_asetus = [200, 9, 9]
    piirra_yksi_laiva(laivaTemp, vari_asetus)
    print("aseta laiva")

    asetus_Kesken = True
    while asetus_Kesken:
        time.sleep(0.3)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sio.disconnect()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    if laivaTemp[0][1] < 9 and laivaTemp[-1][1] < 9:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][1] += 1
                    vari_asetus = [33, 55, 66]
                    for coord in laivaTemp:
                        if laivat[coord[0]][coord[1]]:
                            vari_asetus = [200, 9, 9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                elif event.key == pygame.K_UP:
                    if laivaTemp[0][1] > 0 and laivaTemp[-1][1] > 0:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][1] -= 1
                    vari_asetus = [33, 55, 66]
                    for coord in laivaTemp:
                        if laivat[coord[0]][coord[1]]:
                            vari_asetus = [200, 9, 9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                elif event.key == pygame.K_LEFT:
                    if laivaTemp[0][0] > 0 and laivaTemp[-1][0] > 0:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][0] -= 1
                    vari_asetus = [33, 55, 66]
                    for coord in laivaTemp:
                        if laivat[coord[0]][coord[1]]:
                            vari_asetus = [200, 9, 9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                elif event.key == pygame.K_RIGHT:
                    if laivaTemp[0][0] < 9 and laivaTemp[-1][0] < 9:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][0] += 1
                    vari_asetus = [33, 55, 66]
                    for coord in laivaTemp:
                        if laivat[coord[0]][coord[1]]:
                            vari_asetus = [200, 9, 9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                elif event.key == pygame.K_r:
                    if laivaTemp[0][0] == laivaTemp[-1][0]:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][1] = laivaTemp[0][1]
                            laivaTemp[i][0] = laivaTemp[0][0] + i
                        if laivaTemp[-1][0] > 9:
                            overflow_temp = 9 - laivaTemp[-1][0]
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][0] += overflow_temp
                        vari_asetus = [33, 55, 66]
                        for coord in laivaTemp:
                            if laivat[coord[0]][coord[1]]:
                                vari_asetus = [200, 9, 9]
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp, vari_asetus)
                        continue
                    if laivaTemp[0][1] == laivaTemp[-1][1]:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][0] = laivaTemp[0][0]
                            laivaTemp[i][1] = laivaTemp[0][1] + i
                        if laivaTemp[-1][1] > 9:
                            overflow_temp = 9 - laivaTemp[-1][1]
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][1] += overflow_temp
                        vari_asetus = [33, 55, 66]
                        for coord in laivaTemp:
                            if laivat[coord[0]][coord[1]]:
                                vari_asetus = [200, 9, 9]
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp, vari_asetus)
                elif event.key == pygame.K_y:
                    VoiAsettaa = True
                    for coord in laivaTemp:
                        if laivat[coord[0]][coord[1]]:
                            VoiAsettaa = False
                    if VoiAsettaa:
                        asetus_Kesken = False
                        break
    return laivaTemp

def draw_start_screen():
    screen.fill((0, 0, 0))
    otsikko = fontti.render("Laivanupotus peli :D", True, (255, 255, 255))
    pygame.draw.rect(screen, (50, 50, 200), host_rect)
    pygame.draw.rect(screen, (50, 200, 50), join_rect)
    pygame.draw.rect(screen, (50, 200, 50), laivojen_asetus_rect)
    
    host_text = fontti.render("HOST", True, (255, 255, 255))
    join_text = fontti.render("JOIN", True, (255, 255, 255))
    laivojen_asetus_text = fontti.render("ASETA LAIVAT", True, (255, 255, 255))
    
    screen.blit(otsikko, (LEVEYS // 2 - otsikko.get_width() // 2, 150))
    screen.blit(host_text, (host_rect.x + 35, host_rect.y + 10))
    screen.blit(join_text, (join_rect.x + 35, join_rect.y + 10))
    screen.blit(laivojen_asetus_text, (laivojen_asetus_rect.x + 35, laivojen_asetus_rect.y + 10))
    
    pygame.display.flip()

game_state = "start"  # Peli alkaa start-näkymästä

def main():
    global game_state
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
                    if event.key == pygame.K_h:
                        print("Hosting game...")
                        connect_to_server()
                        start_screen = False
                    elif event.key == pygame.K_j:
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False
                    elif event.key == pygame.K_a:
                        print("Laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if host_rect.collidepoint(event.pos):
                        print("Hosting game...")
                        connect_to_server()
                        start_screen = False
                    elif join_rect.collidepoint(event.pos):
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False
                    elif laivojen_asetus_rect.collidepoint(event.pos):
                        print("Laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()
        elif game_state == "setup_ships":
            print("Siirrytään laivojen asetteluun...")
            screen.fill((255, 255, 255))
            aseta_laivat()
            game_state = "playing"
        elif game_state == "playing":
            screen.fill((0, 50, 0))
            piirra_ruudukko()
            piirra_vihollisen_ruudukko()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    grid_x = int((mouse_x - (LEVEYS/2)) // (LEVEYS/22))
                    grid_y = int(mouse_y // (KORKEUS/11))
                    if 0 <= grid_x < 10 and 0 <= grid_y < 10:
                        print(f"Ampuminen ruutuun: ({grid_x}, {grid_y})")
                        sio.emit('bomb_shot', {"x": grid_x, "y": grid_y})
        pygame.display.flip()

    sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()