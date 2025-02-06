import pygame
import sys
import socket
import threading
import queue

pygame.init()

# -------------------------------------------------------
# Asetukset
# -------------------------------------------------------
LEVEYS = 1024
KORKEUS = 768
RUUDUN_KOKO = 30
RUUTUJA_X = 10
RUUTUJA_Y = 10

HOST_PORT = 5555  # Portti, jota käytetään yhteydenpitoon

kello = pygame.time.Clock()
fontti = pygame.font.SysFont(None, 24)

is_dark_mode = True  # Dark/Light teema

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
        # "Fake" yhteys Googleen, jotta saadaan koneen IP
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
connected = False         # Yhteys on muodostettu (host <-> client)

# Viestien vastaanotto lisätään queue:hun, josta chatbox-luokka voi niitä lukea
incoming_messages = queue.Queue()

def host_thread():
    global server_socket, connection_socket, connected
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("", HOST_PORT))
        server_socket.listen(1)
        print("Odotetaan yhteyttä portissa", HOST_PORT)
        conn, addr = server_socket.accept()
        print("Yhteys saatu:", addr)
        connection_socket = conn
        connected = True
        # Käynnistetään lukusäie
        t = threading.Thread(target=listening_thread, args=(conn,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe host_threadissä:", e)

def join_thread(ip):
    global client_socket, connected
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, HOST_PORT))
        print("Yhdistys onnistui serveriin:", ip)
        connected = True
        # Käynnistetään lukusäie
        t = threading.Thread(target=listening_thread, args=(client_socket,))
        t.daemon = True
        t.start()
    except Exception as e:
        print("Virhe join_threadissä:", e)

def listening_thread(sock):
    """Kuuntelee saapuvat viestit socketista ja pistää ne incoming_messages-queuehen."""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            messages = data.decode("utf-8").split("\n")
            for msg in messages:
                if msg.strip():
                    incoming_messages.put(msg.strip())
        except:
            break
    print("Lukusäie päättyi. Yhteys katkennut?")

def send_message(msg):
    """Lähettää viestin molempiin suuntiin (host/client)."""
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
# ChatBox
# -------------------------------------------------------
class ChatBox:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.messages = []
        self.input_text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                # Lähetä viesti
                if self.input_text.strip():
                    self.messages.append("Sinä: " + self.input_text)
                    send_message("CHAT:" + self.input_text)
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def update(self):
        # Tarkista, onko incoming_messages-queuehen tullut viestejä
        while not incoming_messages.empty():
            msg = incoming_messages.get()
            # Jos viesti alkaa "CHAT:", laitetaan se chatboxiin
            if msg.startswith("CHAT:"):
                content = msg[5:].strip()
                self.messages.append("Vieras: " + content)

    def draw(self, surface):
        theme_data = current_theme()
        pygame.draw.rect(surface, theme_data["bg"], self.rect)
        pygame.draw.rect(surface, theme_data["border"], self.rect, 2)

        # Syötekentän teksti
        input_surface = fontti.render(self.input_text, True, theme_data["text"])
        surface.blit(input_surface, (self.rect.x+5, self.rect.y+self.rect.height-30))

        # Viestit
        offset_y = 5
        # Piirretään max ~10 viestiä
        for msg in reversed(self.messages[-10:]):
            msg_surface = fontti.render(msg, True, theme_data["text"])
            surface.blit(msg_surface, (self.rect.x+5, self.rect.y+offset_y))
            offset_y += 20

# -------------------------------------------------------
# Pääohjelma (state machine)
# -------------------------------------------------------
MAIN_MENU = 0
HOST_SCREEN = 1
JOIN_SCREEN = 2
SHIP_PLACEMENT = 3
GAME_STATE = 4

def main():
    global is_dark_mode, connected
    pygame.display.set_caption("Laivanupotus - esimerkkiverkko")
    screen = pygame.display.set_mode((LEVEYS, KORKEUS))

    state = MAIN_MENU

    # Laudat
    player_board = Board(RUUTUJA_X, RUUTUJA_Y)
    enemy_board = Board(RUUTUJA_X, RUUTUJA_Y)

    # Viralliset laivat
    ship_lengths = [5, 4, 3, 3, 2]
    current_ship_index = 0
    current_ship = Ship(ship_lengths[current_ship_index], 0, 0, horizontal=True)

    chatbox = ChatBox(800, 50, 200, 600)  # Tehdään kookkaampi chat

    host_ip = ""
    join_ip = ""
    player_turn = True

    def draw_main_menu():
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

    def draw_host_screen():
        theme_data = current_theme()
        screen.fill(theme_data["bg"])
        txt1 = fontti.render("Odotetaan pelaajaa liittymään...", True, theme_data["text"])
        screen.blit(txt1, (50, 50))

        # Hostin IP
        myip = get_own_ip()
        txt2 = fontti.render(f"IP: {myip} (port {HOST_PORT})", True, theme_data["text"])
        screen.blit(txt2, (50, 100))

    def draw_join_screen():
        theme_data = current_theme()
        screen.fill(theme_data["bg"])
        info_text = fontti.render("Anna hostin IP:", True, theme_data["text"])
        screen.blit(info_text, (50, 50))

        ip_input = fontti.render(join_ip, True, theme_data["text"])
        screen.blit(ip_input, (50, 100))

        join_hint = fontti.render("Paina ENTER liittyäksesi", True, theme_data["text"])
        screen.blit(join_hint, (50, 150))

    def draw_ship_placement():
        theme_data = current_theme()
        screen.fill(theme_data["bg"])
        ohje_text = "Sijoita laiva nuolinäppäimillä. R kääntää. ENTER hyväksyy laiva."
        ohje = fontti.render(ohje_text, True, theme_data["text"])
        screen.blit(ohje, (20, 20))

        player_board.draw(screen, 50, 100, show_ships=True)
        current_ship.draw(screen, 50, 100)

        chatbox.draw(screen)

    def draw_game_state():
        theme_data = current_theme()
        screen.fill(theme_data["bg"])

        ohje_oma = fontti.render("OMA LAUTA", True, theme_data["text"])
        screen.blit(ohje_oma, (50, 70))
        player_board.draw(screen, 50, 100, show_ships=True)

        ohje_vihu = fontti.render("VIHOLLISEN LAUTA (klikkaa ampua)", True, theme_data["text"])
        screen.blit(ohje_vihu, (400, 70))
        enemy_board.draw(screen, 400, 100, show_ships=False)

        chatbox.draw(screen)

        turn_text = "Sinun vuoro!" if player_turn else "Vastustajan vuoro..."
        vuoro_render = fontti.render(turn_text, True, theme_data["text"])
        screen.blit(vuoro_render, (50, 700))

    running = True
    while running:
        kello.tick(30)
        # Päivitetään chatbox (luetaan incoming_messages).
        chatbox.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            chatbox.handle_event(event)

            if state == MAIN_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    host_rect, join_rect, toggle_rect = draw_main_menu()
                    if host_rect.collidepoint((mx, my)):
                        # Käynnistetään host-thread
                        t = threading.Thread(target=host_thread)
                        t.daemon = True
                        t.start()
                        state = HOST_SCREEN
                    elif join_rect.collidepoint((mx, my)):
                        state = JOIN_SCREEN
                    elif toggle_rect.collidepoint((mx, my)):
                        is_dark_mode = not is_dark_mode

            elif state == HOST_SCREEN:
                # Jos yhteys on syntynyt, siirrytään laivojen sijoitukseen
                if connected:
                    state = SHIP_PLACEMENT

            elif state == JOIN_SCREEN:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Join-thread
                        t = threading.Thread(target=join_thread, args=(join_ip,))
                        t.daemon = True
                        t.start()
                    elif event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    else:
                        join_ip += event.unicode

                # Jos client onnistui yhdistämään
                if connected:
                    state = SHIP_PLACEMENT

            elif state == SHIP_PLACEMENT:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        current_ship.x -= 1
                        if current_ship.x < 0:
                            current_ship.x = 0
                        current_ship.update_positions()
                    elif event.key == pygame.K_RIGHT:
                        current_ship.x += 1
                        if current_ship.horizontal and (current_ship.x + current_ship.length) > RUUTUJA_X:
                            current_ship.x = RUUTUJA_X - current_ship.length
                        current_ship.update_positions()
                    elif event.key == pygame.K_UP:
                        current_ship.y -= 1
                        if current_ship.y < 0:
                            current_ship.y = 0
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
                                current_ship = Ship(ship_lengths[current_ship_index], 0, 0, horizontal=True)
                            else:
                                state = GAME_STATE

            elif state == GAME_STATE:
                if player_turn:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        board_x = (mx - 400) // RUUDUN_KOKO
                        board_y = (my - 100) // RUUDUN_KOKO
                        if 0 <= board_x < RUUTUJA_X and 0 <= board_y < RUUTUJA_Y:
                            osuma = enemy_board.shoot(board_x, board_y)
                            if osuma:
                                print("Osuma!")
                            else:
                                print("Huti!")
                            if enemy_board.all_sunk():
                                print("Voitit pelin!")
                            # Vaihdetaan vuoro
                            player_turn = False
                else:
                    # Tässä pitäisi toteuttaa vastustajan liike (verkosta) 
                    # tai simuloida sitä, nyt vain placeholder
                    pass

        # Piirto
        if state == MAIN_MENU:
            host_rect, join_rect, toggle_rect = draw_main_menu()
        elif state == HOST_SCREEN:
            draw_host_screen()
        elif state == JOIN_SCREEN:
            draw_join_screen()
        elif state == SHIP_PLACEMENT:
            draw_ship_placement()
        elif state == GAME_STATE:
            draw_game_state()

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
