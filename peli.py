import pygame
import sys
import socket
import threading
import queue
import time

pygame.init()

# -------------------------------------------------------
# Asetukset
# -------------------------------------------------------
LEVEYS = 1024
KORKEUS = 768
RUUDUN_KOKO = 30
RUUTUJA_X = 10
RUUTUJA_Y = 10

HOST_PORT = 5555      # TCP-portti varsinaiselle peli-yhteydelle
DISCOVERY_PORT = 5556 # UDP-portti, jota käytetään lan-löytöön

kello = pygame.time.Clock()
fontti = pygame.font.SysFont(None, 24)
iso_fontti = pygame.font.SysFont(None, 60)

# Dark/Light -teema
is_dark_mode = True

dark_theme = {
    "bg": (30, 30, 30),
    "text": (220, 220, 220),
    "grid_bg": (60, 60, 60),
    "shot_miss": (100, 100, 255),
    "shot_hit": (255, 100, 100),
    "ship": (120, 120, 120),
    "border": (200, 200, 200),
    "button_bg": (80, 80, 80),
    "button_hover": (100, 100, 100),
}

light_theme = {
    "bg": (220, 220, 220),
    "text": (20, 20, 20),
    "grid_bg": (200, 200, 200),
    "shot_miss": (0, 0, 255),
    "shot_hit": (255, 0, 0),
    "ship": (150, 150, 150),
    "border": (0, 0, 0),
    "button_bg": (180, 180, 180),
    "button_hover": (160, 160, 160),
}

def current_theme():
    return dark_theme if is_dark_mode else light_theme

def get_own_ip():
    """Hakee paikallisen IP-osoitteen (yksinkertainen tapa)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# -------------------------------------------------------
# Pelirakenteet
# -------------------------------------------------------
class Ship:
    def __init__(self, length, x, y, horizontal=True):
        self.length = length
        self.x = x
        self.y = y
        self.horizontal = horizontal
        self.positions = []
        self.update_positions()

    def update_positions(self):
        self.positions.clear()
        for i in range(self.length):
            if self.horizontal:
                self.positions.append((self.x + i, self.y))
            else:
                self.positions.append((self.x, self.y + i))

    def draw(self, surface, offset_x, offset_y):
        col = current_theme()["ship"]
        bor = current_theme()["border"]
        for (grid_x, grid_y) in self.positions:
            rect = pygame.Rect(offset_x + grid_x * RUUDUN_KOKO,
                               offset_y + grid_y * RUUDUN_KOKO,
                               RUUDUN_KOKO, RUUDUN_KOKO)
            pygame.draw.rect(surface, col, rect)
            pygame.draw.rect(surface, bor, rect, 1)

class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # 0 = ei ammuttu, 1 = ammuttu ohi, 2 = ammuttu osuma
        self.shots = [[0 for _ in range(width)] for _ in range(height)]
        self.ships = []

    def place_ship(self, ship):
        for (x, y) in ship.positions:
            if not (0 <= x < self.width and 0 <= y < self.height):
                return False
        for s in self.ships:
            for pos in s.positions:
                if pos in ship.positions:
                    return False
        self.ships.append(ship)
        return True

    def check_hit(self, x, y):
        for s in self.ships:
            if (x, y) in s.positions:
                return True
        return False

    def shoot(self, x, y):
        if self.shots[y][x] == 0:
            if self.check_hit(x, y):
                self.shots[y][x] = 2
                return True
            else:
                self.shots[y][x] = 1
        return False

    def all_sunk(self):
        for s in self.ships:
            for (x, y) in s.positions:
                if self.shots[y][x] != 2:
                    return False
        return True

    def draw(self, surface, offset_x, offset_y, show_ships=False):
        theme_data = current_theme()
        grid_col = theme_data["grid_bg"]
        border_col = theme_data["border"]
        miss_col = theme_data["shot_miss"]
        hit_col = theme_data["shot_hit"]

        # Koordinaatisto (A–J, 1–10)
        for i in range(self.width):
            letter_label = chr(ord('A') + i)
            label_surf = fontti.render(letter_label, True, theme_data["text"])
            lx = offset_x + i * RUUDUN_KOKO + RUUDUN_KOKO // 2 - label_surf.get_width() // 2
            ly = offset_y - 20
            surface.blit(label_surf, (lx, ly))

        for j in range(self.height):
            number_label = str(j+1)
            label_surf = fontti.render(number_label, True, theme_data["text"])
            nx = offset_x - 25
            ny = offset_y + j * RUUDUN_KOKO + RUUDUN_KOKO//2 - label_surf.get_height()//2
            surface.blit(label_surf, (nx, ny))

        for y in range(self.height):
            for x in range(self.width):
                rect = pygame.Rect(offset_x + x * RUUDUN_KOKO,
                                   offset_y + y * RUUDUN_KOKO,
                                   RUUDUN_KOKO, RUUDUN_KOKO)
                pygame.draw.rect(surface, grid_col, rect)
                if show_ships:
                    for s in self.ships:
                        if (x, y) in s.positions:
                            pygame.draw.rect(surface, theme_data["ship"], rect)

                # Ammutut
                if self.shots[y][x] == 1:
                    pygame.draw.circle(surface, miss_col, rect.center, RUUDUN_KOKO//4)
                elif self.shots[y][x] == 2:
                    pygame.draw.circle(surface, hit_col, rect.center, RUUDUN_KOKO//4)

                pygame.draw.rect(surface, border_col, rect, 1)

# -------------------------------------------------------
# Verkko-luokat: host/client + chat
# -------------------------------------------------------
server_socket = None
client_socket = None
connection_socket = None  # Kun host hyväksyy clientin, se tallettaa sen tänne
connected = False         # Onko varsinainen TCP-yhteys
is_host = None            # True=host, False=client
host_ready = False
client_ready = False

# Pelin vuoro (host aloittaa)
player_turn = False

# Jotta nähdään laukauksen tulos ruudulla
last_shot_result = None
last_shot_timer = 0       # Montako framea vielä näytetään

# Viestien vastaanotto jonoon (chat + muut)
incoming_messages = queue.Queue()

# Discovery-langat ja tietorakenteet
discovery_thread_running = False
found_hosts = []  # client kerää täältä listan
scan_in_progress = False

def host_thread():
    """Luodaan TCP-listen-soketti, odotetaan clientin yhteyttä."""
    global server_socket, connection_socket, connected
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("", HOST_PORT))
        server_socket.listen(1)
        print("Odotetaan yhteyttä portissa", HOST_PORT)
        conn, addr = server_socket.accept()
        print("Yhteys saatu:", addr)
        connection_socket = conn
        # Kun client on yhdistänyt, host ei siirry heti laivan sijoitukseen,
        # vaan odottaa “CLIENT_CONNECTED” -viestiä.
        # (Client lähettää sen kun on saanut connectin auki).
    except Exception as e:
        print("Virhe host_threadissä:", e)

def join_thread(ip):
    """Client yrittää TCP connectia hostin IP:hen."""
    global client_socket, connected
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, HOST_PORT))
        print("Yhdistys onnistui serveriin:", ip)
        # Kerrotaan hostille, että client on paikalla
        send_message("CLIENT_CONNECTED")
        # Käynnistetään lukusäie
        t = threading.Thread(target=listening_thread, args=(client_socket,))
        t.daemon = True
        t.start()
        connected = True
    except Exception as e:
        print("Virhe join_threadissä:", e)

def start_listening_thread_for_host():
    """Kun host on acceptannut yhteyden, käynnistetään lukusäie."""
    global connection_socket, connected
    connected = True
    t = threading.Thread(target=listening_thread, args=(connection_socket,))
    t.daemon = True
    t.start()

def listening_thread(sock):
    """Kuuntelee saapuvat viestit socketista ja puskee incoming_messages -queueen."""
    global connected
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            msgs = data.decode("utf-8").split("\n")
            for m in msgs:
                if m.strip():
                    incoming_messages.put(m.strip())
        except:
            break
    print("listening_thread päättyi, yhteys katkennut?")
    connected = False

def send_message(msg):
    """Lähettää viestin host->client tai client->host -socketille."""
    global connection_socket, client_socket
    if connection_socket:  # Host
        try:
            connection_socket.sendall((msg + "\n").encode("utf-8"))
        except:
            pass
    if client_socket:      # Client
        try:
            client_socket.sendall((msg + "\n").encode("utf-8"))
        except:
            pass

# -------------------------------------------------------
# Discovery: host vastaa broadcastiin, client tekee broadcastin
# -------------------------------------------------------
def discovery_server():
    """Host avaa UDP-soketin, kuuntelee DISCOVER_BATTLESHIP -viestejä, 
       ja vastaa niihin 'BATTLESHIP_HOST'."""
    global discovery_thread_running
    discovery_thread_running = True
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", DISCOVERY_PORT))
    sock.settimeout(1.0)
    try:
        while discovery_thread_running:
            try:
                data, addr = sock.recvfrom(1024)
                if data.decode("utf-8") == "DISCOVER_BATTLESHIP":
                    # Palautetaan “BATTLESHIP_HOST” + ip
                    myip = get_own_ip()
                    response = "BATTLESHIP_HOST:" + myip
                    sock.sendto(response.encode("utf-8"), addr)
            except socket.timeout:
                pass
    finally:
        sock.close()

def scan_for_hosts():
    """Client lähettää broadcastin 'DISCOVER_BATTLESHIP' porttiin 5556 
       ja kuuntelee 2 sekuntia mahdollisia vastauksia."""
    global found_hosts, scan_in_progress
    found_hosts.clear()
    scan_in_progress = True

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(2.0)  # skannataan 2 sekuntia
    try:
        # Lähetä broadcast
        msg = "DISCOVER_BATTLESHIP".encode("utf-8")
        sock.sendto(msg, ("<broadcast>", DISCOVERY_PORT))

        # Odotetaan vastauksia
        start_time = time.time()
        while time.time() - start_time < 2.0:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8")
                if text.startswith("BATTLESHIP_HOST:"):
                    ip = text.split(":")[1]
                    if ip not in found_hosts:
                        found_hosts.append(ip)
            except socket.timeout:
                pass
    finally:
        sock.close()
        scan_in_progress = False

# -------------------------------------------------------
# ChatBox, jossa selkeä input-kenttä
# -------------------------------------------------------
class ChatBox:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        # Viestialue (listaus)
        self.messages_rect = pygame.Rect(x, y, w, h - 40)
        # Input-alue (alareuna)
        self.input_rect = pygame.Rect(x, y + h - 40, w, 40)

        self.messages = []
        self.input_text = ""
        self.active_input = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.input_rect.collidepoint(event.pos):
                self.active_input = True
            else:
                self.active_input = False

        if event.type == pygame.KEYDOWN and self.active_input:
            if event.key == pygame.K_RETURN:
                if self.input_text.strip():
                    self.messages.append("Sinä: " + self.input_text)
                    send_message("CHAT:" + self.input_text)
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def update(self):
        global host_ready, client_ready, player_turn, connection_socket
        while not incoming_messages.empty():
            msg = incoming_messages.get()
            # Chat-viestit
            if msg.startswith("CHAT:"):
                content = msg[5:].strip()
                self.messages.append("Vieras: " + content)

            elif msg == "CLIENT_CONNECTED":
                # Client ilmoittaa hostille kytkeytymisestään
                print("Client ilmoitti olevansa connected.")
                if server_socket and connection_socket:
                    # Nyt vasta käynnistetään listening_thread
                    start_listening_thread_for_host()
                # Host lähettää "BEGIN" = molemmat menköön SHIP_PLACEMENT
                send_message("BEGIN")

            elif msg == "BEGIN":
                # Client puolella: siirrytään laivojen sijoitukseen
                global state
                if state == JOIN_SCREEN:
                    # Join-screen -> laivojen sijoitus
                    print("BEGIN vastaanotettu, siirrytään laivojen sijoitukseen")
                    state = SHIP_PLACEMENT
                elif state == HOST_SCREEN:
                    # Host-screen -> laivojen sijoitus
                    state = SHIP_PLACEMENT

            elif msg == "HOSTREADY":
                host_ready = True
            elif msg == "CLIENTREADY":
                client_ready = True

            elif msg == "SWITCHTURN":
                player_turn = True

            elif msg.startswith("AMMO:"):
                # Esimerkki, jos haluaisimme synkronoida ammunnan
                # (Ei toteuteta loppuun tässä demossa)
                pass

    def draw(self, surface):
        theme_data = current_theme()
        # Piirretään chatin tausta
        pygame.draw.rect(surface, theme_data["bg"], self.rect)
        pygame.draw.rect(surface, theme_data["border"], self.rect, 2)

        # Piirretään viestilistaus-alue
        pygame.draw.rect(surface, theme_data["bg"], self.messages_rect)
        pygame.draw.rect(surface, theme_data["border"], self.messages_rect, 1)

        # Piirretään input-alue
        pygame.draw.rect(surface, theme_data["bg"], self.input_rect)
        # Korostus jos aktiivinen
        if self.active_input:
            pygame.draw.rect(surface, (100, 200, 100), self.input_rect, 2)
        else:
            pygame.draw.rect(surface, theme_data["border"], self.input_rect, 2)

        # Syötekentän teksti
        input_surface = fontti.render(self.input_text, True, theme_data["text"])
        surface.blit(input_surface, (self.input_rect.x+5, self.input_rect.y+10))

        # Viestit (scrollataan alas)
        offset_y = 5
        for msg in reversed(self.messages[-15:]):
            msg_surface = fontti.render(msg, True, theme_data["text"])
            surface.blit(msg_surface, (self.messages_rect.x+5, self.messages_rect.y+offset_y))
            offset_y += 20

# -------------------------------------------------------
# Pääohjelma (state machine)
# -------------------------------------------------------
MAIN_MENU = 0
HOST_SCREEN = 1
JOIN_SCREEN = 2
SHIP_PLACEMENT = 3
GAME_STATE = 4
state = MAIN_MENU  # Globaali, jotta chatbox pääsee muuttamaan sitä

player_board = Board(RUUTUJA_X, RUUTUJA_Y)
enemy_board = Board(RUUTUJA_X, RUUTUJA_Y)

# Viralliset laivat
ship_lengths = [5, 4, 3, 3, 2]
current_ship_index = 0
current_ship = Ship(ship_lengths[current_ship_index], 0, 0, horizontal=True)

chatbox = ChatBox(800, 50, 200, 600)

join_ip = ""  # Client syöttää
scan_button_rect = pygame.Rect(50, 200, 150, 40)  # SCAN-nappi
host_list_rects = []  # klikkausalueet IP-listalle

def draw_main_menu(screen):
    theme_data = current_theme()
    screen.fill(theme_data["bg"])

    otsikko = fontti.render("Tervetuloa Laivanupotuspeliin!", True, theme_data["text"])
    screen.blit(otsikko, (LEVEYS//2 - otsikko.get_width()//2, 50))

    host_btn_rect = pygame.Rect(LEVEYS//2 - 100, 150, 200, 50)
    join_btn_rect = pygame.Rect(LEVEYS//2 - 100, 220, 200, 50)

    mx, my = pygame.mouse.get_pos()

    # HOST nappi
    if host_btn_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme_data["button_hover"], host_btn_rect)
    else:
        pygame.draw.rect(screen, theme_data["button_bg"], host_btn_rect)
    pygame.draw.rect(screen, theme_data["border"], host_btn_rect, 2)
    host_label = fontti.render("HOST PELI", True, theme_data["text"])
    screen.blit(host_label, (host_btn_rect.centerx - host_label.get_width()//2,
                             host_btn_rect.centery - host_label.get_height()//2))

    # JOIN nappi
    if join_btn_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme_data["button_hover"], join_btn_rect)
    else:
        pygame.draw.rect(screen, theme_data["button_bg"], join_btn_rect)
    pygame.draw.rect(screen, theme_data["border"], join_btn_rect, 2)
    join_label = fontti.render("JOIN PELI", True, theme_data["text"])
    screen.blit(join_label, (join_btn_rect.centerx - join_label.get_width()//2,
                             join_btn_rect.centery - join_label.get_height()//2))

    # Toggle dark/light
    toggle_rect = pygame.Rect(10, 10, 100, 40)
    if toggle_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme_data["button_hover"], toggle_rect)
    else:
        pygame.draw.rect(screen, theme_data["button_bg"], toggle_rect)
    pygame.draw.rect(screen, theme_data["border"], toggle_rect, 2)

    mode_text = "Light Mode" if is_dark_mode else "Dark Mode"
    toggle_label = fontti.render(mode_text, True, theme_data["text"])
    screen.blit(toggle_label, (toggle_rect.centerx - toggle_label.get_width()//2,
                               toggle_rect.centery - toggle_label.get_height()//2))

    return host_btn_rect, join_btn_rect, toggle_rect

def draw_host_screen(screen):
    theme_data = current_theme()
    screen.fill(theme_data["bg"])
    txt1 = fontti.render("Odotetaan pelaajaa liittymään...", True, theme_data["text"])
    screen.blit(txt1, (50, 50))

    # Hostin IP
    myip = get_own_ip()
    txt2 = fontti.render(f"IP: {myip} (port {HOST_PORT})", True, theme_data["text"])
    screen.blit(txt2, (50, 100))

def draw_join_screen(screen):
    global scan_button_rect, host_list_rects
    theme_data = current_theme()
    screen.fill(theme_data["bg"])
    info_text = fontti.render("Anna hostin IP manuaalisesti:", True, theme_data["text"])
    screen.blit(info_text, (50, 50))

    ip_input = fontti.render(join_ip, True, theme_data["text"])
    screen.blit(ip_input, (50, 80))

    join_hint = fontti.render("Paina ENTER liittyäksesi", True, theme_data["text"])
    screen.blit(join_hint, (50, 110))

    # SCAN-nappi
    mx, my = pygame.mouse.get_pos()
    if scan_button_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme_data["button_hover"], scan_button_rect)
    else:
        pygame.draw.rect(screen, theme_data["button_bg"], scan_button_rect)
    pygame.draw.rect(screen, theme_data["border"], scan_button_rect, 2)
    scan_label = fontti.render("SCAN LAN", True, theme_data["text"])
    screen.blit(scan_label, (scan_button_rect.centerx - scan_label.get_width()//2,
                             scan_button_rect.centery - scan_label.get_height()//2))

    # Lista löydetyistä hosteista
    y_offset = 250
    host_list_rects.clear()
    for idx, ip in enumerate(found_hosts):
        r = pygame.Rect(50, y_offset, 200, 30)
        host_list_rects.append((r, ip))
        if r.collidepoint((mx, my)):
            pygame.draw.rect(screen, theme_data["button_hover"], r)
        else:
            pygame.draw.rect(screen, theme_data["button_bg"], r)
        pygame.draw.rect(screen, theme_data["border"], r, 1)

        ip_label = fontti.render(ip, True, theme_data["text"])
        screen.blit(ip_label, (r.x+5, r.y+5))
        y_offset += 40

def draw_ship_placement(screen):
    theme_data = current_theme()
    screen.fill(theme_data["bg"])
    ohje_text = "Sijoita laiva nuolinäppäimillä. R kääntää. ENTER hyväksyy laiva."
    ohje = fontti.render(ohje_text, True, theme_data["text"])
    screen.blit(ohje, (20, 20))

    player_board.draw(screen, 50, 100, show_ships=True)
    current_ship.draw(screen, 50, 100)

    # Näytetään, jos vain toinen on valmis
    if is_host:
        if host_ready and not client_ready:
            wait_txt = fontti.render("Odotetaan toista pelaajaa...", True, theme_data["text"])
            screen.blit(wait_txt, (50, 70))
    else:
        if client_ready and not host_ready:
            wait_txt = fontti.render("Odotetaan toista pelaajaa...", True, theme_data["text"])
            screen.blit(wait_txt, (50, 70))

    chatbox.draw(screen)

def draw_game_state(screen):
    global last_shot_result, last_shot_timer
    theme_data = current_theme()
    screen.fill(theme_data["bg"])

    ohje_oma = fontti.render("OMA LAUTA", True, theme_data["text"])
    screen.blit(ohje_oma, (50, 70))
    player_board.draw(screen, 50, 100, show_ships=True)

    ohje_vihu = fontti.render("VIHOLLISEN LAUTA (klikkaa ampua)", True, theme_data["text"])
    screen.blit(ohje_vihu, (400, 70))
    enemy_board.draw(screen, 400, 100, show_ships=False)

    # Näytetään, onko osuma/huti (hetken aikaa)
    if last_shot_result and last_shot_timer > 0:
        text = iso_fontti.render(last_shot_result.upper(), True, (255, 0, 0))
        screen.blit(text, (LEVEYS//2 - text.get_width()//2, 20))

    # Vuoro
    turn_text = "Sinun vuoro!" if player_turn else "Vastustajan vuoro..."
    vuoro_render = fontti.render(turn_text, True, theme_data["text"])
    screen.blit(vuoro_render, (50, 700))

    chatbox.draw(screen)

def main():
    global is_dark_mode, connected, is_host
    global host_ready, client_ready, player_turn
    global state, join_ip
    global current_ship_index, current_ship
    global last_shot_result, last_shot_timer
    global discovery_thread_running

    pygame.display.set_caption("Laivanupotuspeli - laajennettu esimerkki")
    screen = pygame.display.set_mode((LEVEYS, KORKEUS))

    # Käynnistetään "discovery_server"-säie, jos olemme host.
    # Tehdään se vasta sitten, kun painetaan "HOST" (katso alla event-käsittely).
    # Alustetaan se vain None:ksi
    discovery_server_thread = None

    running = True
    while running:
        kello.tick(30)
        chatbox.update()

        # Päivitetään osuma/huti -teksti pois ruudulta ~1 sekunnin päästä
        if last_shot_timer > 0:
            last_shot_timer -= 1
            if last_shot_timer <= 0:
                last_shot_result = None

        # Jos molemmat valmiita laivan sijoituksessa => GAME_STATE
        if state == SHIP_PLACEMENT and host_ready and client_ready:
            state = GAME_STATE
            # Jos host => host aloittaa
            if is_host:
                player_turn = True
            else:
                player_turn = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            chatbox.handle_event(event)

            if state == MAIN_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    host_rect, join_rect, toggle_rect = draw_main_menu(screen)
                    mx, my = event.pos
                    if host_rect.collidepoint((mx, my)):
                        # HOST
                        is_host = True
                        # Luodaan TCP-listen -säie
                        t = threading.Thread(target=host_thread)
                        t.daemon = True
                        t.start()
                        # Käynnistetään discovery_server -säie
                        discovery_server_thread = threading.Thread(target=discovery_server)
                        discovery_server_thread.daemon = True
                        discovery_server_thread.start()

                        state = HOST_SCREEN

                    elif join_rect.collidepoint((mx, my)):
                        is_host = False
                        # Pelkkä client => ei discovery_server
                        state = JOIN_SCREEN

                    elif toggle_rect.collidepoint((mx, my)):
                        is_dark_mode = not is_dark_mode

            elif state == HOST_SCREEN:
                # Host on avannut socketin, odottaa acceptia.
                # Kun host saa “CLIENT_CONNECTED” -viestin, chatbox.update() hoitaa:
                # se lähettää "BEGIN" => molemmat siirtyvät SHIP_PLACEMENT
                pass

            elif state == JOIN_SCREEN:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    # SCAN-nappi
                    if scan_button_rect.collidepoint((mx, my)):
                        # Käynnistetään scannaus
                        t = threading.Thread(target=scan_for_hosts)
                        t.daemon = True
                        t.start()
                    else:
                        # Katsotaan klikkasiko jotakin IP-listaa
                        for (r, ipaddr) in host_list_rects:
                            if r.collidepoint((mx, my)):
                                # Yritä connect
                                t = threading.Thread(target=join_thread, args=(ipaddr,))
                                t.daemon = True
                                t.start()
                                break

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Yritetään joinia syötettyyn IP:hen
                        t = threading.Thread(target=join_thread, args=(join_ip,))
                        t.daemon = True
                        t.start()
                    elif event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    else:
                        join_ip += event.unicode

                # HUOM: Siirtyminen SHIP_PLACEMENT -tilaan clientilla tapahtuu,
                # kun se saa "BEGIN"-viestin hostilta (chatbox.update()).

            elif state == SHIP_PLACEMENT:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        current_ship.x = max(current_ship.x - 1, 0)
                        current_ship.update_positions()
                    elif event.key == pygame.K_RIGHT:
                        current_ship.x += 1
                        if current_ship.horizontal and (current_ship.x + current_ship.length) > RUUTUJA_X:
                            current_ship.x = RUUTUJA_X - current_ship.length
                        current_ship.update_positions()
                    elif event.key == pygame.K_UP:
                        current_ship.y = max(current_ship.y - 1, 0)
                        current_ship.update_positions()
                    elif event.key == pygame.K_DOWN:
                        current_ship.y += 1
                        if not current_ship.horizontal and (current_ship.y + current_ship.length) > RUUTUJA_Y:
                            current_ship.y = RUUTUJA_Y - current_ship.length
                        current_ship.update_positions()
                    elif event.key == pygame.K_r:
                        current_ship.horizontal = not current_ship.horizontal
                        if current_ship.horizontal:
                            if current_ship.x + current_ship.length > RUUTUJA_X:
                                current_ship.x = RUUTUJA_X - current_ship.length
                        else:
                            if current_ship.y + current_ship.length > RUUTUJA_Y:
                                current_ship.y = RUUTUJA_Y - current_ship.length
                        current_ship.update_positions()

                    elif event.key == pygame.K_RETURN:
                        if player_board.place_ship(current_ship):
                            current_ship_index += 1
                            if current_ship_index < len(ship_lengths):
                                current_ship = Ship(ship_lengths[current_ship_index], 0, 0, True)
                            else:
                                # Pelaaja valmis
                                if is_host:
                                    host_ready = True
                                    send_message("HOSTREADY")
                                else:
                                    client_ready = True
                                    send_message("CLIENTREADY")

            elif state == GAME_STATE:
                if player_turn:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        board_x = (mx - 400) // RUUDUN_KOKO
                        board_y = (my - 100) // RUUDUN_KOKO
                        if 0 <= board_x < RUUTUJA_X and 0 <= board_y < RUUTUJA_Y:
                            osuma = enemy_board.shoot(board_x, board_y)
                            if osuma:
                                last_shot_result = "OSUMA!"
                                print("Osuma!")
                            else:
                                last_shot_result = "HUTI!"
                                print("Huti!")
                            last_shot_timer = 30  # näytetään ~1s

                            if enemy_board.all_sunk():
                                print("Voitit pelin!")
                            # Vuoro vaihtuu
                            player_turn = False
                            send_message("SWITCHTURN")

        # Piirto
        if state == MAIN_MENU:
            host_rect, join_rect, toggle_rect = draw_main_menu(screen)
        elif state == HOST_SCREEN:
            draw_host_screen(screen)
        elif state == JOIN_SCREEN:
            draw_join_screen(screen)
        elif state == SHIP_PLACEMENT:
            draw_ship_placement(screen)
        elif state == GAME_STATE:
            draw_game_state(screen)

        pygame.display.flip()

    # Suljetaan sovellus
    # Lopetetaan discovery_server, jos käynnissä
    if discovery_server_thread and discovery_server_thread.is_alive():
        global discovery_thread_running
        discovery_thread_running = False
        discovery_server_thread.join()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
