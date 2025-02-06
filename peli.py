import pygame
import sys
import socket
import threading
import queue
import time

pygame.init()
pygame.mixer.init()

# -------------------------------------------------------
# Ladataan äänet ja grafiikat
# -------------------------------------------------------
try:
    bomb_sound = pygame.mixer.Sound("bomb.wav")
except:
    bomb_sound = None

try:
    explosion_image = pygame.image.load("explosion.png").convert_alpha()
except:
    explosion_image = None

# -------------------------------------------------------
# Asetukset
# -------------------------------------------------------
LEVEYS = 1024
KORKEUS = 768
RUUDUN_KOKO = 30
RUUTUJA_X = 10
RUUTUJA_Y = 10

HOST_PORT = 5555       # TCP-portti pelille
DISCOVERY_PORT = 5556  # UDP-portti LAN-scan -toiminnolle (broadcast)

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
# Muuttujia, jotka oltava ennen funktioita,
# jotta global toimii virheittä
# -------------------------------------------------------
discovery_thread_running = False
discovery_thread = None

found_hosts = []
scan_in_progress = False


# -------------------------------------------------------
# Laiva ja lauta
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
        for (gx, gy) in self.positions:
            rx = offset_x + gx * RUUDUN_KOKO
            ry = offset_y + gy * RUUDUN_KOKO
            rect = pygame.Rect(rx, ry, RUUDUN_KOKO, RUUDUN_KOKO)
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
        # Tarkista rajat
        for (x, y) in ship.positions:
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                return False
        # Tarkista päällekkäisyys
        for s in self.ships:
            for pos in s.positions:
                if pos in ship.positions:
                    return False
        self.ships.append(ship)
        return True

    def add_raw_positions(self, positions):
        """Tallentaa jokaisen (x,y)-ruudun yksittäisenä laivana (demo)."""
        for (x,y) in positions:
            s = Ship(1, x, y, True)
            self.ships.append(s)

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

        # Koordinaatisto
        for i in range(self.width):
            letter = chr(ord('A') + i)
            label_surf = fontti.render(letter, True, theme_data["text"])
            lx = offset_x + i*RUUDUN_KOKO + RUUDUN_KOKO//2 - label_surf.get_width()//2
            ly = offset_y - 20
            surface.blit(label_surf, (lx, ly))

        for j in range(self.height):
            number_label = str(j+1)
            label_surf = fontti.render(number_label, True, theme_data["text"])
            nx = offset_x - 25
            ny = offset_y + j*RUUDUN_KOKO + RUUDUN_KOKO//2 - label_surf.get_height()//2
            surface.blit(label_surf, (nx, ny))

        for row in range(self.height):
            for col in range(self.width):
                rx = offset_x + col * RUUDUN_KOKO
                ry = offset_y + row * RUUDUN_KOKO
                rect = pygame.Rect(rx, ry, RUUDUN_KOKO, RUUDUN_KOKO)
                pygame.draw.rect(surface, grid_col, rect)
                # Näytetään laivat
                if show_ships:
                    for s in self.ships:
                        if (col, row) in s.positions:
                            pygame.draw.rect(surface, theme_data["ship"], rect)

                val = self.shots[row][col]
                if val == 1:
                    pygame.draw.circle(surface, miss_col, rect.center, RUUDUN_KOKO//4)
                elif val == 2:
                    pygame.draw.circle(surface, hit_col, rect.center, RUUDUN_KOKO//4)

                pygame.draw.rect(surface, border_col, rect, 1)


# -------------------------------------------------------
# LAN Discovery (SCAN)
# -------------------------------------------------------
def discovery_server():
    """
    Host vastaa broadcast-kyselyihin: kun client lähettää "DISCOVER_BATTLESHIP",
    host lähettää "BATTLESHIP_HOST:<hostin_ip>".
    """
    global discovery_thread_running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", DISCOVERY_PORT))
    sock.settimeout(1.0)

    myip = get_own_ip()
    try:
        while discovery_thread_running:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8")
                if text == "DISCOVER_BATTLESHIP":
                    response = f"BATTLESHIP_HOST:{myip}"
                    sock.sendto(response.encode("utf-8"), addr)
            except socket.timeout:
                pass
    finally:
        sock.close()


def scan_for_hosts():
    """
    Client lähettää broadcastin "DISCOVER_BATTLESHIP" porttiin 5556,
    odottaa 2s, ja tallentaa vastaukset found_hosts-listaan.
    """
    global found_hosts, scan_in_progress
    found_hosts.clear()
    scan_in_progress = True

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(2.0)

    try:
        msg = "DISCOVER_BATTLESHIP".encode("utf-8")
        sock.sendto(msg, ("<broadcast>", DISCOVERY_PORT))

        start_t = time.time()
        while time.time() - start_t < 2.0:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8").strip()
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
# Verkko (TCP)
# -------------------------------------------------------
server_socket = None
client_socket = None
connection_socket = None
connected = False

incoming_messages = queue.Queue()

def host_thread():
    """Host odottaa clientin connectia."""
    global server_socket, connection_socket, connected
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("", HOST_PORT))
        server_socket.listen(1)
        print("HOST: Odotetaan yhteyttä portissa", HOST_PORT)
        conn, addr = server_socket.accept()
        print("HOST: Yhteys saatu:", addr)
        connection_socket = conn
        connected = True
        # Lukusäie
        t = threading.Thread(target=listening_thread, args=(connection_socket,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe host_thread:", e)

def join_thread(ip):
    """Client yrittää yhdistää hostiin."""
    global client_socket, connected
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, HOST_PORT))
        print("CLIENT: Yhdistys onnistui serveriin:", ip)
        connected = True
        # Lukusäie
        t = threading.Thread(target=listening_thread, args=(client_socket,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe join_thread:", e)

def listening_thread(sock):
    """Kuuntelee viestejä, puskee incoming_messages-queueen."""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            parts = data.decode("utf-8").split("\n")
            for p in parts:
                if p.strip():
                    incoming_messages.put(p.strip())
        except:
            break
    print("listening_thread päättyi, yhteys katkennut?")

def send_message(msg):
    global connection_socket, client_socket
    out = (msg + "\n").encode("utf-8")
    if connection_socket:
        try:
            connection_socket.sendall(out)
        except:
            pass
    if client_socket:
        try:
            client_socket.sendall(out)
        except:
            pass


# -------------------------------------------------------
# ChatBox
# -------------------------------------------------------
class ChatBox:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.messages_rect = pygame.Rect(x, y, w, h - 40)
        self.input_rect = pygame.Rect(x, y + h - 40, w, 40)

        self.messages = []
        self.input_text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.input_rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False

        if event.type == pygame.KEYDOWN and self.active:
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
        global state, player_turn, enemy_board, player_board
        global ships_placed, enemy_ships_placed
        global last_shot_result, last_shot_timer, last_shot_coords

        while not incoming_messages.empty():
            msg = incoming_messages.get()
            # CHAT
            if msg.startswith("CHAT:"):
                text = msg[5:].strip()
                self.messages.append("Vieras: " + text)

            # ALLSHIPS
            elif msg.startswith("ALLSHIPS:"):
                coords_str = msg[len("ALLSHIPS:"):].strip()
                coords_pairs = coords_str.split()
                positions = []
                for cp in coords_pairs:
                    sx, sy = cp.split(",")
                    x, y = int(sx), int(sy)
                    positions.append((x,y))
                # Tallennetaan enemy_boardiin
                enemy_board.add_raw_positions(positions)
                enemy_ships_placed = True
                print("Vastustajan laivat vastaanotettu")

            # SHOOT
            elif msg.startswith("SHOOT:"):
                xy_str = msg[len("SHOOT:"):].strip()
                sx, sy = xy_str.split(",")
                tx, ty = int(sx), int(sy)
                # Vastustaja ampuu meitä
                was_hit = player_board.shoot(tx, ty)
                if was_hit:
                    if player_board.all_sunk():
                        # Kaikki uponneet => vastustaja voitti => RESULT:hit win
                        send_message("RESULT:hit win")
                    else:
                        send_message("RESULT:hit")
                else:
                    send_message("RESULT:miss")

            # RESULT
            elif msg.startswith("RESULT:"):
                parts = msg.split()
                main_part = parts[0]  # esim. RESULT:hit
                got_win = False
                if len(parts)>1 and parts[1] == "win":
                    got_win = True

                if main_part == "RESULT:hit":
                    # Merkitään edellinen laukaus osumaksi
                    if last_shot_coords:
                        (xx, yy) = last_shot_coords
                        enemy_board.shots[yy][xx] = 2
                    last_shot_result = "OSUMA!"
                    last_shot_timer = 30

                elif main_part == "RESULT:miss":
                    if last_shot_coords:
                        (xx, yy) = last_shot_coords
                        enemy_board.shots[yy][xx] = 1
                    last_shot_result = "HUTI!"
                    last_shot_timer = 30

                if got_win:
                    # Me (ampuja) voitimme
                    print("Saimme RESULT:hit win => voitimme")
                    state = WIN_SCREEN
                else:
                    # Vuoro vaihtuu
                    player_turn = False
                    send_message("SWITCHTURN")

            elif msg == "SWITCHTURN":
                # Nyt me saamme vuoron
                player_turn = True

            elif msg == "YOU_LOSE":
                # Vihollinen kertoi että hävisimme
                print("YOU_LOSE => state=LOSE_SCREEN")
                state = LOSE_SCREEN

    def draw(self, surface):
        theme_data = current_theme()
        pygame.draw.rect(surface, theme_data["bg"], self.rect)
        pygame.draw.rect(surface, theme_data["border"], self.rect, 2)

        # Messages-alue
        pygame.draw.rect(surface, theme_data["bg"], self.messages_rect)
        pygame.draw.rect(surface, theme_data["border"], self.messages_rect, 1)

        # Input-alue
        if self.active:
            color = (100, 255, 100)
        else:
            color = theme_data["border"]
        pygame.draw.rect(surface, theme_data["bg"], self.input_rect)
        pygame.draw.rect(surface, color, self.input_rect, 2)

        # Teksti inputissa
        txtsurf = fontti.render(self.input_text, True, theme_data["text"])
        surface.blit(txtsurf, (self.input_rect.x+5, self.input_rect.y+10))

        # Viestilista
        offset_y = 5
        for m in reversed(self.messages[-15:]):
            msurf = fontti.render(m, True, theme_data["text"])
            surface.blit(msurf, (self.messages_rect.x+5, self.messages_rect.y+offset_y))
            offset_y += 20


# -------------------------------------------------------
# Peli: tilat, muuttujat
# -------------------------------------------------------
MAIN_MENU = 0
HOST_SCREEN = 1
JOIN_SCREEN = 2
SHIP_PLACEMENT = 3
GAME_STATE = 4
WIN_SCREEN = 5
LOSE_SCREEN = 6

state = MAIN_MENU

player_board = Board(RUUTUJA_X, RUUTUJA_Y)
enemy_board = Board(RUUTUJA_X, RUUTUJA_Y)

ship_lengths = [5,4,3,3,2]
current_ship_index = 0
current_ship = Ship(ship_lengths[current_ship_index], 0, 0, True)

chatbox = ChatBox(800, 50, 200, 600)

player_turn = False
ships_placed = False
enemy_ships_placed = False

join_ip = ""

last_shot_coords = None
last_shot_result = None
last_shot_timer = 0

# LAN-scan UI
scan_button_rect = pygame.Rect(50, 200, 150, 40)
host_list_rects = []

def draw_main_menu(screen):
    theme = current_theme()
    screen.fill(theme["bg"])

    otsikko = fontti.render("Tervetuloa Laivanupotuspeliin!", True, theme["text"])
    screen.blit(otsikko, (LEVEYS//2 - otsikko.get_width()//2, 50))

    host_btn_rect = pygame.Rect(LEVEYS//2 - 100, 150, 200, 50)
    join_btn_rect = pygame.Rect(LEVEYS//2 - 100, 220, 200, 50)

    mx, my = pygame.mouse.get_pos()

    # HOST nappi
    if host_btn_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], host_btn_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], host_btn_rect)
    pygame.draw.rect(screen, theme["border"], host_btn_rect, 2)
    host_label = fontti.render("HOST PELI", True, theme["text"])
    screen.blit(host_label, (host_btn_rect.centerx - host_label.get_width()//2,
                             host_btn_rect.centery - host_label.get_height()//2))

    # JOIN nappi
    if join_btn_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], join_btn_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], join_btn_rect)
    pygame.draw.rect(screen, theme["border"], join_btn_rect, 2)
    join_label = fontti.render("JOIN PELI", True, theme["text"])
    screen.blit(join_label, (join_btn_rect.centerx - join_label.get_width()//2,
                             join_btn_rect.centery - join_label.get_height()//2))

    # Toggle dark/light
    toggle_rect = pygame.Rect(10, 10, 100, 40)
    if toggle_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], toggle_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], toggle_rect)
    pygame.draw.rect(screen, theme["border"], toggle_rect, 2)

    mode_text = "Light Mode" if is_dark_mode else "Dark Mode"
    toggle_label = fontti.render(mode_text, True, theme["text"])
    screen.blit(toggle_label, (toggle_rect.centerx - toggle_label.get_width()//2,
                               toggle_rect.centery - toggle_label.get_height()//2))

    return host_btn_rect, join_btn_rect, toggle_rect


def draw_host_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    t1 = fontti.render("Odotetaan pelaajaa liittymään...", True, theme["text"])
    screen.blit(t1, (50, 50))

    ipaddr = get_own_ip()
    t2 = fontti.render(f"IP: {ipaddr} (port {HOST_PORT})", True, theme["text"])
    screen.blit(t2, (50, 80))


def draw_join_screen(screen):
    global host_list_rects
    theme = current_theme()
    screen.fill(theme["bg"])

    info_text = fontti.render("Anna hostin IP manuaalisesti:", True, theme["text"])
    screen.blit(info_text, (50, 50))

    ip_surf = fontti.render(join_ip, True, theme["text"])
    screen.blit(ip_surf, (50, 80))

    join_hint = fontti.render("Paina ENTER liittyäksesi", True, theme["text"])
    screen.blit(join_hint, (50, 110))

    # SCAN-nappi
    mx, my = pygame.mouse.get_pos()
    if scan_button_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], scan_button_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], scan_button_rect)
    pygame.draw.rect(screen, theme["border"], scan_button_rect, 2)

    scan_label = fontti.render("SCAN LAN", True, theme["text"])
    screen.blit(scan_label, (scan_button_rect.centerx - scan_label.get_width()//2,
                             scan_button_rect.centery - scan_label.get_height()//2))

    # Lista löydetyistä hosteista
    y_offset = 250
    host_list_rects.clear()
    for ipaddr in found_hosts:
        r = pygame.Rect(50, y_offset, 200, 30)
        host_list_rects.append((r, ipaddr))
        if r.collidepoint((mx, my)):
            pygame.draw.rect(screen, theme["button_hover"], r)
        else:
            pygame.draw.rect(screen, theme["button_bg"], r)
        pygame.draw.rect(screen, theme["border"], r, 1)

        ip_label = fontti.render(ipaddr, True, theme["text"])
        screen.blit(ip_label, (r.x+5, r.y+5))

        y_offset += 40


def draw_ship_placement(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    ohje = fontti.render("Sijoita laiva nuolinäppäimillä, R kääntää, ENTER hyväksyy.", True, theme["text"])
    screen.blit(ohje, (20, 20))

    player_board.draw(screen, 50, 100, show_ships=True)
    current_ship.draw(screen, 50, 100)

    if enemy_ships_placed:
        info = fontti.render("Vastustaja on sijoittanut laivansa.", True, theme["text"])
        screen.blit(info, (50, 70))

    chatbox.draw(screen)


def draw_game_state(screen):
    global last_shot_result, last_shot_timer
    theme = current_theme()
    screen.fill(theme["bg"])

    ohje_oma = fontti.render("OMA LAUTA", True, theme["text"])
    screen.blit(ohje_oma, (50,70))
    player_board.draw(screen, 50, 100, show_ships=True)

    ohje_vihu = fontti.render("VIHOLLISEN LAUTA (klikkaa ampua)", True, theme["text"])
    screen.blit(ohje_vihu, (400,70))
    enemy_board.draw(screen, 400, 100, show_ships=False)

    if last_shot_result and last_shot_timer>0:
        bigtext = iso_fontti.render(last_shot_result, True, (255,0,0))
        screen.blit(bigtext, (LEVEYS//2 - bigtext.get_width()//2, 20))
        if explosion_image:
            ex_rect = explosion_image.get_rect()
            ex_rect.center = (LEVEYS//2, 120)
            screen.blit(explosion_image, ex_rect)

    turn_text = "Sinun vuoro!" if player_turn else "Vastustajan vuoro..."
    t = fontti.render(turn_text, True, theme["text"])
    screen.blit(t, (50, 700))

    chatbox.draw(screen)


def draw_win_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    txt = iso_fontti.render("VOITIT PELIN!", True, (255,0,0))
    screen.blit(txt, (LEVEYS//2 - txt.get_width()//2, KORKEUS//2 - txt.get_height()//2))

def draw_lose_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    txt = iso_fontti.render("HÄVISIT PELIN!", True, (255,0,0))
    screen.blit(txt, (LEVEYS//2 - txt.get_width()//2, KORKEUS//2 - txt.get_height()//2))


def main():
    global state, is_host, connected, join_ip
    global current_ship_index, current_ship
    global ships_placed, enemy_ships_placed, player_turn
    global last_shot_coords, last_shot_result, last_shot_timer
    global discovery_thread_running, discovery_thread

    pygame.display.set_caption("Laivanupotuspeli - LAN-scan + synkronointi")
    screen = pygame.display.set_mode((LEVEYS, KORKEUS))

    running = True

    while running:
        kello.tick(30)
        chatbox.update()

        # Päivitetään OSUMA/HUTI
        if last_shot_timer>0:
            last_shot_timer -= 1
            if last_shot_timer<=0:
                last_shot_result = None

        # Jos host on HOST_SCREEN ja connected => SHIP_PLACEMENT
        if state == HOST_SCREEN and connected:
            state = SHIP_PLACEMENT
        # Jos client on JOIN_SCREEN ja connected => SHIP_PLACEMENT
        if state == JOIN_SCREEN and connected:
            state = SHIP_PLACEMENT

        # Jos laivat + vastustajan laivat valmiit => GAME_STATE
        if state == SHIP_PLACEMENT and ships_placed and enemy_ships_placed:
            state = GAME_STATE
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
                    mx, my = event.pos
                    hbtn, jbtn, toggle_rect = draw_main_menu(screen)
                    if hbtn.collidepoint((mx,my)):
                        # HOST
                        is_host = True
                        # Käynnistetään host TCP-lanka
                        t = threading.Thread(target=host_thread)
                        t.daemon = True
                        t.start()

                        # Käynnistetään discovery_server-lanka, jotta clientin SCAN saa vastauksen
                        discovery_thread_running = True
                        discovery_thread = threading.Thread(target=discovery_server)
                        discovery_thread.daemon = True
                        discovery_thread.start()

                        state = HOST_SCREEN

                    elif jbtn.collidepoint((mx,my)):
                        is_host = False
                        state = JOIN_SCREEN

                    elif toggle_rect.collidepoint((mx,my)):
                        is_dark_mode = not is_dark_mode

            elif state == HOST_SCREEN:
                pass

            elif state == JOIN_SCREEN:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    # SCAN-nappi
                    if scan_button_rect.collidepoint((mx, my)):
                        # Käynnistetään SCAN-lanka
                        st = threading.Thread(target=scan_for_hosts)
                        st.daemon = True
                        st.start()
                    else:
                        # Katsotaan klikkaus listaan
                        for (r, ipaddr) in host_list_rects:
                            if r.collidepoint((mx,my)):
                                # Join-lanka
                                t = threading.Thread(target=join_thread, args=(ipaddr,))
                                t.daemon = True
                                t.start()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Yritetään join syötetylle IP:lle
                        t = threading.Thread(target=join_thread, args=(join_ip,))
                        t.daemon = True
                        t.start()
                    elif event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    else:
                        join_ip += event.unicode

            elif state == SHIP_PLACEMENT:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        current_ship.x = max(current_ship.x - 1, 0)
                        current_ship.update_positions()
                    elif event.key == pygame.K_RIGHT:
                        current_ship.x += 1
                        if current_ship.horizontal and (current_ship.x + current_ship.length)>RUUTUJA_X:
                            current_ship.x = RUUTUJA_X - current_ship.length
                        current_ship.update_positions()
                    elif event.key == pygame.K_UP:
                        current_ship.y = max(current_ship.y - 1, 0)
                        current_ship.update_positions()
                    elif event.key == pygame.K_DOWN:
                        current_ship.y += 1
                        if not current_ship.horizontal and (current_ship.y + current_ship.length)>RUUTUJA_Y:
                            current_ship.y = RUUTUJA_Y - current_ship.length
                        current_ship.update_positions()
                    elif event.key == pygame.K_r:
                        current_ship.horizontal = not current_ship.horizontal
                        # clamp
                        if current_ship.horizontal:
                            if current_ship.x + current_ship.length > RUUTUJA_X:
                                current_ship.x = RUUTUJA_X - current_ship.length
                        else:
                            if current_ship.y + current_ship.length > RUUTUJA_Y:
                                current_ship.y = RUUTUJA_Y - current_ship.length
                        current_ship.update_positions()

                    elif event.key == pygame.K_RETURN:
                        # Yritetään sijoittaa
                        if player_board.place_ship(current_ship):
                            current_ship_index += 1
                            if current_ship_index < len(ship_lengths):
                                current_ship = Ship(ship_lengths[current_ship_index], 0, 0, True)
                            else:
                                # Kaikki laivat asetettu => lähetetään ALLSHIPS
                                all_positions = []
                                for s in player_board.ships:
                                    all_positions.extend(s.positions)
                                pos_strs = [f"{x},{y}" for (x,y) in all_positions]
                                msg = "ALLSHIPS:" + " ".join(pos_strs)
                                send_message(msg)
                                ships_placed = True

            elif state == GAME_STATE:
                # Ammunta vain jos oma vuoro
                if player_turn:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        bx = (mx - 400)//RUUTUJA_KOKO
                        by = (my - 100)//RUUTUJA_KOKO
                        if 0<=bx<RUUTUJA_X and 0<=by<RUUTUJA_Y:
                            # Soitetaan ääni
                            if bomb_sound:
                                bomb_sound.play()
                            # SHOOT
                            send_message(f"SHOOT:{bx},{by}")
                            last_shot_coords = (bx, by)
                            # passivoidaan itsemme, lopullinen vuoronvaihto
                            # hoituu RESULT/ SWITCHTURN -viesteillä
                            player_turn = False

            elif state == WIN_SCREEN or state == LOSE_SCREEN:
                pass

        # Piirto
        if state == MAIN_MENU:
            draw_main_menu(screen)
        elif state == HOST_SCREEN:
            draw_host_screen(screen)
        elif state == JOIN_SCREEN:
            draw_join_screen(screen)
        elif state == SHIP_PLACEMENT:
            draw_ship_placement(screen)
        elif state == GAME_STATE:
            draw_game_state(screen)
        elif state == WIN_SCREEN:
            draw_win_screen(screen)
        elif state == LOSE_SCREEN:
            draw_lose_screen(screen)

        pygame.display.flip()

    # Suljetaan
    discovery_thread_running = False
    if discovery_thread and discovery_thread.is_alive():
        discovery_thread.join()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
