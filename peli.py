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
    explosion_image = None  # Jos ei löydy tiedostoa, ohitetaan

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

# Teemat (dark/light)
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
        self.positions = []
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
        # Tarkista meneekö laiva laudan sisään
        for (x, y) in ship.positions:
            if not (0 <= x < self.width and 0 <= y < self.height):
                return False
        # Tarkista päällekkäisyydet
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
        # Palauttaa True jos kaikki laivat uponneet
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

        # Piirretään koordinaatisto (A..J, 1..10)
        for i in range(self.width):
            letter_label = chr(ord('A') + i)
            lsurf = fontti.render(letter_label, True, theme_data["text"])
            lx = offset_x + i * RUUDUN_KOKO + (RUUDUN_KOKO // 2 - lsurf.get_width() // 2)
            ly = offset_y - 20
            surface.blit(lsurf, (lx, ly))

        for j in range(self.height):
            number_label = str(j + 1)
            nsurf = fontti.render(number_label, True, theme_data["text"])
            nx = offset_x - 25
            ny = offset_y + j * RUUDUN_KOKO + (RUUDUN_KOKO // 2 - nsurf.get_height() // 2)
            surface.blit(nsurf, (nx, ny))

        # Piirretään ruudut
        for ry in range(self.height):
            for rx in range(self.width):
                rect = pygame.Rect(offset_x + rx * RUUDUN_KOKO,
                                   offset_y + ry * RUUDUN_KOKO,
                                   RUUDUN_KOKO, RUUDUN_KOKO)
                pygame.draw.rect(surface, grid_col, rect)
                if show_ships:
                    # Näytä laiva
                    for s in self.ships:
                        if (rx, ry) in s.positions:
                            pygame.draw.rect(surface, theme_data["ship"], rect)
                # Ammuttu
                val = self.shots[ry][rx]
                if val == 1:
                    pygame.draw.circle(surface, miss_col, rect.center, RUUDUN_KOKO // 4)
                elif val == 2:
                    pygame.draw.circle(surface, hit_col, rect.center, RUUDUN_KOKO // 4)
                pygame.draw.rect(surface, border_col, rect, 1)

# -------------------------------------------------------
# Verkko
# -------------------------------------------------------
server_socket = None
client_socket = None
connection_socket = None
connected = False
is_host = None  # True=host, False=client

# Tila, jonka molemmat pelaajat saavat, kun yhteys on syntynyt
# Hoidetaan yksinkertaisesti: host -> kun accept OK, server_thread asettaa connected=True
# client -> kun connect OK => connected=True

incoming_messages = queue.Queue()

def host_thread():
    """Host odottaa yhtä asiakasta (client)."""
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
        # Käynnistetään lukusäie
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
        # Käynnistetään lukusäie
        t = threading.Thread(target=listening_thread, args=(client_socket,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe join_thread:", e)

def listening_thread(sock):
    """Vastaanottaa viestejä, puskee incoming_messages-jonoon."""
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
    """Lähettää viestin toiseen päähän."""
    global connection_socket, client_socket
    out = (msg + "\n").encode("utf-8")
    if connection_socket:  # Host
        try:
            connection_socket.sendall(out)
        except:
            pass
    if client_socket:      # Client
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
                # Lähetä chat
                if self.input_text.strip():
                    self.messages.append("Sinä: " + self.input_text)
                    send_message("CHAT:" + self.input_text)
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def update(self):
        while not incoming_messages.empty():
            msg = incoming_messages.get()
            if msg.startswith("CHAT:"):
                content = msg[5:].strip()
                self.messages.append("Vieras: " + content)
            elif msg == "SWITCHTURN":
                # Meidän vuoro
                global player_turn
                player_turn = True

    def draw(self, surface):
        theme_data = current_theme()
        pygame.draw.rect(surface, theme_data["bg"], self.rect)
        pygame.draw.rect(surface, theme_data["border"], self.rect, 2)

        # Messages area
        pygame.draw.rect(surface, theme_data["bg"], self.messages_rect)
        pygame.draw.rect(surface, theme_data["border"], self.messages_rect, 1)

        # Input area
        if self.active:
            color = (100, 255, 100)
        else:
            color = theme_data["border"]
        pygame.draw.rect(surface, theme_data["bg"], self.input_rect)
        pygame.draw.rect(surface, color, self.input_rect, 2)

        # Teksti inputissa
        txtsurf = fontti.render(self.input_text, True, theme_data["text"])
        surface.blit(txtsurf, (self.input_rect.x+5, self.input_rect.y+10))

        # Viestilista (max ~15)
        offset_y = 5
        for m in reversed(self.messages[-15:]):
            msurf = fontti.render(m, True, theme_data["text"])
            surface.blit(msurf, (self.messages_rect.x+5, self.messages_rect.y+offset_y))
            offset_y += 20

# -------------------------------------------------------
# Pelitilat (state)
# -------------------------------------------------------
MAIN_MENU = 0
HOST_SCREEN = 1
JOIN_SCREEN = 2
SHIP_PLACEMENT = 3
GAME_STATE = 4

state = MAIN_MENU
host_ip = ""
join_ip = ""
player_turn = False  # Host aloittaa, kun laivat on asetettu

player_board = Board(RUUTUJA_X, RUUTUJA_Y)
enemy_board = Board(RUUTUJA_X, RUUTUJA_Y)

ship_lengths = [5,4,3,3,2]
current_ship_index = 0
current_ship = Ship(ship_lengths[current_ship_index], 0, 0, True)

#  Pieni logiikka iskun visuaaliseen näyttämiseen
last_shot_result = None
last_shot_timer = 0

chatbox = ChatBox(800, 50, 200, 600)

# Laivojen sijoituksen "valmius"
ships_placed = False
enemy_ships_placed = False  # (oikeassa pelissä pitäisi sopia protokolla, milloin vastustaja on valmis)

def draw_main_menu(screen):
    theme = current_theme()
    screen.fill(theme["bg"])

    t = fontti.render("Tervetuloa Laivanupotuspeliin!", True, theme["text"])
    screen.blit(t, (LEVEYS//2 - t.get_width()//2, 50))

    host_btn = pygame.Rect(LEVEYS//2 - 100, 150, 200, 50)
    join_btn = pygame.Rect(LEVEYS//2 - 100, 220, 200, 50)

    mx, my = pygame.mouse.get_pos()

    # HOST
    if host_btn.collidepoint((mx,my)):
        pygame.draw.rect(screen, theme["button_hover"], host_btn)
    else:
        pygame.draw.rect(screen, theme["button_bg"], host_btn)
    pygame.draw.rect(screen, theme["border"], host_btn, 2)
    label_host = fontti.render("HOST PELI", True, theme["text"])
    screen.blit(label_host, (host_btn.centerx - label_host.get_width()//2,
                             host_btn.centery - label_host.get_height()//2))

    # JOIN
    if join_btn.collidepoint((mx,my)):
        pygame.draw.rect(screen, theme["button_hover"], join_btn)
    else:
        pygame.draw.rect(screen, theme["button_bg"], join_btn)
    pygame.draw.rect(screen, theme["border"], join_btn, 2)
    label_join = fontti.render("JOIN PELI", True, theme["text"])
    screen.blit(label_join, (join_btn.centerx - label_join.get_width()//2,
                             join_btn.centery - label_join.get_height()//2))

    # Toggle dark/light
    toggle_rect = pygame.Rect(10,10,100,40)
    if toggle_rect.collidepoint((mx,my)):
        pygame.draw.rect(screen, theme["button_hover"], toggle_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], toggle_rect)
    pygame.draw.rect(screen, theme["border"], toggle_rect, 2)

    mode_text = "Light Mode" if is_dark_mode else "Dark Mode"
    toggle_label = fontti.render(mode_text, True, theme["text"])
    screen.blit(toggle_label, (toggle_rect.centerx - toggle_label.get_width()//2,
                               toggle_rect.centery - toggle_label.get_height()//2))

    return host_btn, join_btn, toggle_rect

def draw_host_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    t1 = fontti.render("Odotetaan pelaajaa liittymään...", True, theme["text"])
    screen.blit(t1, (50,50))

    ipaddr = get_own_ip()
    t2 = fontti.render(f"IP: {ipaddr} (port {HOST_PORT})", True, theme["text"])
    screen.blit(t2, (50,80))

def draw_join_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    t = fontti.render("Anna hostin IP:", True, theme["text"])
    screen.blit(t, (50,50))

    ip_surf = fontti.render(join_ip, True, theme["text"])
    screen.blit(ip_surf, (50,80))

    hint = fontti.render("Paina ENTER liittyäksesi", True, theme["text"])
    screen.blit(hint, (50,110))

def draw_ship_placement(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    ohje = "Sijoita laiva (nuoli + R kääntää, ENTER hyväksyy)."
    rend = fontti.render(ohje, True, theme["text"])
    screen.blit(rend, (20,20))

    player_board.draw(screen, 50, 100, show_ships=True)
    current_ship.draw(screen, 50, 100)

    chatbox.draw(screen)

def draw_game_state(screen):
    global last_shot_result, last_shot_timer
    theme = current_theme()
    screen.fill(theme["bg"])

    # Omalla puolella laivat
    o_teksti = fontti.render("OMA LAUTA", True, theme["text"])
    screen.blit(o_teksti, (50,70))
    player_board.draw(screen, 50, 100, show_ships=True)

    # Vihollisen lauta
    v_teksti = fontti.render("VIHOLLISEN LAUTA (klikkaa ampua)", True, theme["text"])
    screen.blit(v_teksti, (400,70))
    enemy_board.draw(screen, 400, 100, show_ships=False)

    # Näytetään osuma/huti
    if last_shot_result and last_shot_timer>0:
        big = iso_fontti.render(last_shot_result, True, (255,0,0))
        screen.blit(big, (LEVEYS//2 - big.get_width()//2, 20))

    turn_text = "Sinun vuoro!" if player_turn else "Vastustajan vuoro..."
    rend = fontti.render(turn_text, True, theme["text"])
    screen.blit(rend, (50,700))

    chatbox.draw(screen)

def main():
    global state, is_dark_mode, is_host, connected, join_ip
    global current_ship_index, current_ship, ships_placed, enemy_ships_placed
    global player_turn, last_shot_result, last_shot_timer

    pygame.display.set_caption("Laivanupotuspeli - korjattu esimerkki")
    screen = pygame.display.set_mode((LEVEYS, KORKEUS))

    running = True
    while running:
        kello.tick(30)
        chatbox.update()

        # Pieni logiikka: poistetaan OSUMA/HUTI-teksti n. 1s kuluttua
        if last_shot_timer>0:
            last_shot_timer -= 1
            if last_shot_timer<=0:
                last_shot_result = None

        # Jos host on HOST_SCREEN ja connected => molemmat menköön SHIP_PLACEMENT
        if state == HOST_SCREEN and connected:
            state = SHIP_PLACEMENT
        # Jos client on JOIN_SCREEN ja connected => siirtyy SHIP_PLACEMENT
        if state == JOIN_SCREEN and connected:
            state = SHIP_PLACEMENT

        # Jos laivat asetettu => (ships_placed=True),
        # siirrytään GAME_STATE. Host aloittaa
        if state == SHIP_PLACEMENT and ships_placed:
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
                    host_btn, join_btn, toggle_rect = draw_main_menu(screen)
                    if host_btn.collidepoint((mx,my)):
                        is_host = True
                        # Käynnistetään host-thread
                        t = threading.Thread(target=host_thread)
                        t.daemon = True
                        t.start()
                        state = HOST_SCREEN
                    elif join_btn.collidepoint((mx,my)):
                        is_host = False
                        state = JOIN_SCREEN
                    elif toggle_rect.collidepoint((mx,my)):
                        is_dark_mode = not is_dark_mode

            elif state == HOST_SCREEN:
                # Odotetaan client-yhteyttä
                pass

            elif state == JOIN_SCREEN:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Yritetään yhdistää
                        t = threading.Thread(target=join_thread, args=(join_ip,))
                        t.daemon = True
                        t.start()
                    elif event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    else:
                        join_ip += event.unicode

            elif state == SHIP_PLACEMENT:
                # Liikutellaan / käännetään laivaa
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
                        if (not current_ship.horizontal) and (current_ship.y + current_ship.length) > RUUTUJA_Y:
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
                                # Kaikki laivat asetettu
                                ships_placed = True

            elif state == GAME_STATE:
                # Ammunta vain jos oma vuoro
                if player_turn:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        bx = (mx - 400) // RUUDUN_KOKO
                        by = (my - 100) // RUUDUN_KOKO
                        if 0 <= bx < RUUTUJA_X and 0 <= by < RUUTUJA_Y:
                            # Soitetaan pommiääni
                            if bomb_sound:
                                bomb_sound.play()
                            # Tehdään "osuma/huti" local-luokassa
                            was_hit = enemy_board.shoot(bx, by)
                            if was_hit:
                                last_shot_result = "OSUMA!"
                            else:
                                last_shot_result = "HUTI!"
                            last_shot_timer = 30  # n. 1s

                            if enemy_board.all_sunk():
                                print("Voitit pelin!")
                            # Vuoro vaihtuu
                            player_turn = False
                            send_message("SWITCHTURN")

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

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
