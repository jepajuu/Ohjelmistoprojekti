import pygame
import sys
import socket
import threading
import queue
import time

pygame.init()
pygame.mixer.init()

# Ladataan äänet ja grafiikat
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

HOST_PORT = 5555  # TCP-portti

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
    """Hakee paikallisen IP:n (yksinkertainen tapa)."""
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
        # Tarkistetaan rajat ja päällekkäisyydet
        for (x, y) in ship.positions:
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                return False
        for s in self.ships:
            for pos in s.positions:
                if pos in ship.positions:
                    return False
        self.ships.append(ship)
        return True

    def add_raw_positions(self, positions):
        """
        Vastaanottaa listan ruutuja (x,y), joista jokainen kuuluu johonkin laivaan.
        Muodostetaan laivat yksinkertaisesti: jokainen ruutu = laiva pituudella 1
        (Demo). Tai ryhmittele halutessasi. 
        """
        for (x, y) in positions:
            # Tehdään "1-ruudun laiva"
            s = Ship(1, x, y, horizontal=True)
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

        # Kirjaimet
        for i in range(self.width):
            letter_label = chr(ord('A') + i)
            lsurf = fontti.render(letter_label, True, theme_data["text"])
            lx = offset_x + i * RUUDUN_KOKO + RUUDUN_KOKO//2 - lsurf.get_width()//2
            ly = offset_y - 20
            surface.blit(lsurf, (lx, ly))

        # Numerot
        for j in range(self.height):
            number_label = str(j+1)
            nsurf = fontti.render(number_label, True, theme_data["text"])
            nx = offset_x - 25
            ny = offset_y + j * RUUDUN_KOKO + RUUDUN_KOKO//2 - nsurf.get_height()//2
            surface.blit(nsurf, (nx, ny))

        # Ruutu
        for row in range(self.height):
            for col in range(self.width):
                rect = pygame.Rect(offset_x + col * RUUDUN_KOKO,
                                   offset_y + row * RUUDUN_KOKO,
                                   RUUDUN_KOKO, RUUDUN_KOKO)
                pygame.draw.rect(surface, grid_col, rect)
                # Näytetään laivat
                if show_ships:
                    for s in self.ships:
                        if (col, row) in s.positions:
                            pygame.draw.rect(surface, theme_data["ship"], rect)

                # Ammutut
                val = self.shots[row][col]
                if val == 1:
                    pygame.draw.circle(surface, miss_col, rect.center, RUUDUN_KOKO//4)
                elif val == 2:
                    pygame.draw.circle(surface, hit_col, rect.center, RUUDUN_KOKO//4)

                pygame.draw.rect(surface, border_col, rect, 1)

# -------------------------------------------------------
# Verkkotoiminnot
# -------------------------------------------------------
server_socket = None
client_socket = None
connection_socket = None
connected = False
is_host = None  # True = host, False = client

incoming_messages = queue.Queue()

def host_thread():
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
        t = threading.Thread(target=listening_thread, args=(connection_socket,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe host_thread:", e)

def join_thread(ip):
    global client_socket, connected
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, HOST_PORT))
        print("CLIENT: Yhdistys onnistui serveriin:", ip)
        connected = True
        t = threading.Thread(target=listening_thread, args=(client_socket,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe join_thread:", e)

def listening_thread(sock):
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
        self.messages_rect = pygame.Rect(x, y, w, h-40)
        self.input_rect = pygame.Rect(x, y+h-40, w, 40)

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
        global last_shot_result, last_shot_timer

        while not incoming_messages.empty():
            msg = incoming_messages.get()
            # CHAT
            if msg.startswith("CHAT:"):
                text = msg[5:].strip()
                self.messages.append("Vieras: " + text)

            # Vastustaja on lähettänyt laivansa koordinaatit
            elif msg.startswith("ALLSHIPS:"):
                # Muodostetaan list of (x,y)
                # Muoto: ALLSHIPS:x1,y1 x2,y2 x3,y3 ...
                coords_str = msg[len("ALLSHIPS:"):].strip()
                coords_pairs = coords_str.split()
                positions = []
                for cp in coords_pairs:
                    x_str, y_str = cp.split(",")
                    x, y = int(x_str), int(y_str)
                    positions.append((x, y))
                # Tallennetaan ne "enemy_board" => nyt tiedämme vastustajan laivat
                enemy_board.add_raw_positions(positions)
                enemy_ships_placed = True
                print("Saimme vastustajan laivojen koordinaatit, enemy_ships_placed=True")

            # Ammunta
            elif msg.startswith("SHOOT:"):
                # SHOOT:x,y
                xy_str = msg[len("SHOOT:"):].strip()
                sx, sy = xy_str.split(",")
                tx, ty = int(sx), int(sy)

                # Vastustaja ampuu meitä -> tarkistamme omat laivamme (player_board)
                was_hit = player_board.shoot(tx, ty)
                if was_hit:
                    # Jos kaikki uponneet, ilmoitamme voiton ampujalle
                    if player_board.all_sunk():
                        send_message("RESULT:hit win")
                    else:
                        send_message("RESULT:hit")
                else:
                    send_message("RESULT:miss")

            elif msg.startswith("RESULT:"):
                # RESULT:hit / RESULT:hit win / RESULT:miss
                parts = msg.split()
                main_part = parts[0]  # "RESULT:hit" tms.
                # Onko "win" merkkijono kakkososassa?
                got_win = False
                if len(parts) > 1 and parts[1] == "win":
                    got_win = True

                if main_part == "RESULT:hit":
                    # Päivitetään local "enemy_board" viimeksi ammuttuun ruutuun
                    # Emme suoraan tiedä, mihin x,y ammuttiin -> pidämme sen tallessa "last_shot_coords"?
                    # (Demossa tallennamme sen globaaliin)
                    global last_shot_coords
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
                    # Vastustaja kertoi: "RESULT:hit win" => me voitimme
                    # ... koska ampuja voittaa
                    # Oikeasti se tarkoittaa, että vastustajan laivat loppuivat
                    # => me olemme "WINNER"
                    print("Saimme RESULT:hit win => voitimme")
                    state = WIN_SCREEN

                # Vuoro ei vaihdu, ampuja pysyy samana vain jos haluaa ns. "jatkuvat osumat"
                # Oletetaan, että aina vuoro siirtyy
                player_turn = False
                send_message("SWITCHTURN")

            elif msg == "SWITCHTURN":
                # Nyt me saamme vuoron
                player_turn = True

            elif msg == "YOU_LOSE":
                # Vastustaja ilmoitti, että me hävisimme
                print("YOU_LOSE vastaanotettu => state=LOSE_SCREEN")
                state = LOSE_SCREEN

# -------------------------------------------------------
# Pelitilat
# -------------------------------------------------------
MAIN_MENU = 0
HOST_SCREEN = 1
JOIN_SCREEN = 2
SHIP_PLACEMENT = 3
GAME_STATE = 4
WIN_SCREEN = 5
LOSE_SCREEN = 6

state = MAIN_MENU

# Pelin sisäisiä globaaleja
player_board = Board(RUUTUJA_X, RUUTUJA_Y)
enemy_board = Board(RUUTUJA_X, RUUTUJA_Y)

ship_lengths = [5, 4, 3, 3, 2]
current_ship_index = 0
current_ship = Ship(ship_lengths[current_ship_index], 0, 0, True)

chatbox = ChatBox(800, 50, 200, 600)

player_turn = False      # Kuka aloittaa? (host aloittaa kun laivat on valmiit)
ships_placed = False     # Omat laivat
enemy_ships_placed = False  # Vastustajan laivat

join_ip = ""

# Kun ampuja lähettää SHOOT, tallennamme koordinaatit:
last_shot_coords = None
last_shot_result = None
last_shot_timer = 0

def draw_main_menu(screen):
    theme = current_theme()
    screen.fill(theme["bg"])

    t = fontti.render("Tervetuloa Laivanupotuspeliin!", True, theme["text"])
    screen.blit(t, (LEVEYS//2 - t.get_width()//2, 50))

    host_btn = pygame.Rect(LEVEYS//2 - 100, 150, 200, 50)
    join_btn = pygame.Rect(LEVEYS//2 - 100, 220, 200, 50)

    mx, my = pygame.mouse.get_pos()

    # HOST nappi
    if host_btn.collidepoint((mx,my)):
        pygame.draw.rect(screen, theme["button_hover"], host_btn)
    else:
        pygame.draw.rect(screen, theme["button_bg"], host_btn)
    pygame.draw.rect(screen, theme["border"], host_btn, 2)
    host_label = fontti.render("HOST PELI", True, theme["text"])
    screen.blit(host_label, (host_btn.centerx - host_label.get_width()//2,
                             host_btn.centery - host_label.get_height()//2))

    # JOIN nappi
    if join_btn.collidepoint((mx,my)):
        pygame.draw.rect(screen, theme["button_hover"], join_btn)
    else:
        pygame.draw.rect(screen, theme["button_bg"], join_btn)
    pygame.draw.rect(screen, theme["border"], join_btn, 2)
    join_label = fontti.render("JOIN PELI", True, theme["text"])
    screen.blit(join_label, (join_btn.centerx - join_label.get_width()//2,
                             join_btn.centery - join_label.get_height()//2))

    # Toggle
    toggle_rect = pygame.Rect(10,10,100,40)
    if toggle_rect.collidepoint((mx,my)):
        pygame.draw.rect(screen, theme["button_hover"], toggle_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], toggle_rect)
    pygame.draw.rect(screen, theme["border"], toggle_rect, 2)
    mode_text = "Light Mode" if is_dark_mode else "Dark Mode"
    mt = fontti.render(mode_text, True, theme["text"])
    screen.blit(mt, (toggle_rect.centerx - mt.get_width()//2,
                     toggle_rect.centery - mt.get_height()//2))

    return host_btn, join_btn, toggle_rect

def draw_host_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    info = fontti.render("Odotetaan pelaajaa liittymään...", True, theme["text"])
    screen.blit(info, (50,50))

    ipaddr = get_own_ip()
    iptxt = fontti.render(f"IP: {ipaddr} (port {HOST_PORT})", True, theme["text"])
    screen.blit(iptxt, (50,80))

def draw_join_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    txt = fontti.render("Anna hostin IP:", True, theme["text"])
    screen.blit(txt, (50,50))
    ip_surf = fontti.render(join_ip, True, theme["text"])
    screen.blit(ip_surf, (50,80))

    hint = fontti.render("ENTER => yhdistä", True, theme["text"])
    screen.blit(hint, (50,110))

def draw_ship_placement(screen):
    theme = current_theme()
    screen.fill(theme["bg"])

    ohje = "Sijoita laiva (nuolet + R, ENTER hyväksyy)."
    r = fontti.render(ohje, True, theme["text"])
    screen.blit(r, (20,20))

    player_board.draw(screen, 50, 100, show_ships=True)
    current_ship.draw(screen, 50, 100)
    # Näytä, onko vastustaja jo laivat antanut
    if enemy_ships_placed:
        info = fontti.render("Vastustaja on laittanut laivansa.", True, theme["text"])
        screen.blit(info, (50,70))

    chatbox.draw(screen)

def draw_game_state(screen):
    global last_shot_result, last_shot_timer
    theme = current_theme()
    screen.fill(theme["bg"])

    ohje1 = fontti.render("OMA LAUTA", True, theme["text"])
    screen.blit(ohje1, (50,70))
    player_board.draw(screen, 50, 100, show_ships=True)

    ohje2 = fontti.render("VIHOLLISEN LAUTA (klikkaa ampua)", True, theme["text"])
    screen.blit(ohje2, (400,70))
    enemy_board.draw(screen, 400, 100, show_ships=False)

    # Näytetään osuma/huti + explosion
    if last_shot_result and last_shot_timer>0:
        big = iso_fontti.render(last_shot_result, True, (255,0,0))
        screen.blit(big, (LEVEYS//2 - big.get_width()//2, 20))
        # Räjähdyskuva
        if explosion_image:
            ex_rect = explosion_image.get_rect()
            ex_rect.center = (LEVEYS//2, 100)
            screen.blit(explosion_image, ex_rect)

    turn_text = "Sinun vuoro!" if player_turn else "Vastustajan vuoro..."
    vt = fontti.render(turn_text, True, theme["text"])
    screen.blit(vt, (50,700))

    chatbox.draw(screen)

def draw_win_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    wtxt = iso_fontti.render("VOITIT PELIN!", True, (255,0,0))
    screen.blit(wtxt, (LEVEYS//2 - wtxt.get_width()//2, KORKEUS//2 - wtxt.get_height()//2))

def draw_lose_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    ltxt = iso_fontti.render("HÄVISIT PELIN!", True, (255,0,0))
    screen.blit(ltxt, (LEVEYS//2 - ltxt.get_width()//2, KORKEUS//2 - ltxt.get_height()//2))

def main():
    global state, is_host, connected, join_ip
    global current_ship_index, current_ship
    global ships_placed, enemy_ships_placed
    global player_turn, last_shot_result, last_shot_timer
    global last_shot_coords

    pygame.display.set_caption("Laivanupotuspeli - Synkronoitu versio")
    screen = pygame.display.set_mode((LEVEYS, KORKEUS))

    running = True
    while running:
        kello.tick(30)
        chatbox.update()

        # Päivitetään OSUMA/HUTI-teksti
        if last_shot_timer>0:
            last_shot_timer -= 1
            if last_shot_timer<=0:
                last_shot_result = None

        # Jos host on HOST_SCREEN ja connected => siirrytään SHIP_PLACEMENT
        if state == HOST_SCREEN and connected:
            state = SHIP_PLACEMENT

        # Jos client on JOIN_SCREEN ja connected => siirrytään SHIP_PLACEMENT
        if state == JOIN_SCREEN and connected:
            state = SHIP_PLACEMENT

        # Jos molemmat laivat asetettu (ships_placed ja enemy_ships_placed), siirrytään GAME_STATE
        if state == SHIP_PLACEMENT and ships_placed and enemy_ships_placed:
            state = GAME_STATE
            # Host aloittaa
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
                    h_btn, j_btn, tog = draw_main_menu(screen)
                    if h_btn.collidepoint((mx,my)):
                        is_host = True
                        t = threading.Thread(target=host_thread)
                        t.daemon = True
                        t.start()
                        state = HOST_SCREEN
                    elif j_btn.collidepoint((mx,my)):
                        is_host = False
                        state = JOIN_SCREEN
                    elif tog.collidepoint((mx,my)):
                        global is_dark_mode
                        is_dark_mode = not is_dark_mode

            elif state == HOST_SCREEN:
                # Odotetaan client-yhteyttä
                pass

            elif state == JOIN_SCREEN:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        t = threading.Thread(target=join_thread, args=(join_ip,))
                        t.daemon = True
                        t.start()
                    elif event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    else:
                        join_ip += event.unicode

            elif state == SHIP_PLACEMENT:
                # Liikutellaan laivaa
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        current_ship.x = max(current_ship.x - 1, 0)
                        current_ship.update_positions()
                    elif event.key == pygame.K_RIGHT:
                        current_ship.x += 1
                        # clamp
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
                        # clamp
                        if current_ship.horizontal:
                            if current_ship.x + current_ship.length > RUUTUJA_X:
                                current_ship.x = RUUTUJA_X - current_ship.length
                        else:
                            if current_ship.y + current_ship.length > RUUTUJA_Y:
                                current_ship.y = RUUTUJA_Y - current_ship.length
                        current_ship.update_positions()

                    elif event.key == pygame.K_RETURN:
                        # Yritetään sijoittaa laiva
                        if player_board.place_ship(current_ship):
                            current_ship_index += 1
                            if current_ship_index < len(ship_lengths):
                                current_ship = Ship(ship_lengths[current_ship_index], 0, 0, True)
                            else:
                                # Kaikki laivat on asetettu -> lähetetään ALLSHIPS
                                # kerätään jokaisen laivan jokainen ruutu
                                all_positions = []
                                for s in player_board.ships:
                                    all_positions.extend(s.positions)

                                # Luodaan viesti "ALLSHIPS:x,y x,y x,y..."
                                pos_strs = []
                                for (xx, yy) in all_positions:
                                    pos_strs.append(f"{xx},{yy}")
                                full_str = "ALLSHIPS:" + " ".join(pos_strs)
                                send_message(full_str)
                                ships_placed = True

            elif state == GAME_STATE:
                # Ammunta vain jos oma vuoro
                if player_turn:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        bx = (mx - 400)//RUUDUN_KOKO
                        by = (my - 100)//RUUDUN_KOKO
                        if 0 <= bx < RUUTUJA_X and 0 <= by < RUUTUJA_Y:
                            # Soitetaan ääniefekti
                            if bomb_sound:
                                bomb_sound.play()
                            # Lähetetään SHOOT
                            send_message(f"SHOOT:{bx},{by}")
                            # Muistetaan, mihin ammuttiin
                            last_shot_coords = (bx, by)
                            # Vuoro loppuu, mutta lopullinen vuoronvaihto
                            # tulee RESULT-viestistä (nykylogiikassa chatbox.update()).
                            # Jos haluat heti passivoida -> player_turn=False
                            # (Tehdään niin)
                            player_turn = False

            elif state == WIN_SCREEN or state == LOSE_SCREEN:
                # Ei toiminnallisuutta, peli päättynyt
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

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
