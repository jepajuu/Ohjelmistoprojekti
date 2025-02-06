import pygame
import sys
import socket
import threading
import queue
import time

pygame.init()
pygame.font.init()

# -------------------------------------------------------
# Asetukset
# -------------------------------------------------------
LEVEYS = 800
KORKEUS = 600

HOST_PORT = 5555       # TCP-portti
DISCOVERY_PORT = 5556  # UDP-portti LAN-scan -toiminnolle

# -------------------------------------------------------
# Teemat (Dark / Light)
# -------------------------------------------------------
is_dark_mode = True
dark_theme = {
    "bg": (30, 30, 30),
    "text": (220, 220, 220),
    "button_bg": (80, 80, 80),
    "button_hover": (100, 100, 100),
    "border": (200, 200, 200)
}
light_theme = {
    "bg": (220, 220, 220),
    "text": (20, 20, 20),
    "button_bg": (180, 180, 180),
    "button_hover": (160, 160, 160),
    "border": (0, 0, 0)
}

def current_theme():
    return dark_theme if is_dark_mode else light_theme

# -------------------------------------------------------
# Apufunktio: Oma IP-osoite
# -------------------------------------------------------
def get_own_ip():
    """Hakee paikallisen IP-osoitteen."""
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
# LAN Discovery (UDP)
# -------------------------------------------------------
discovery_thread_running = False
discovery_thread = None
found_hosts = []
scan_in_progress = False

def discovery_server():
    """
    Vastaa LAN-broadcast -kyselyihin.
    Kun client lähettää "DISCOVER_BATTLESHIP", lähetetään takaisin
    "BATTLESHIP_HOST:<oma_ip>".
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
    Lähettää broadcastin "DISCOVER_BATTLESHIP" ja kerää vastaukset
    found_hosts-listaan.
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
    """
    Host-tilassa odotetaan TCP-yhteyttä portissa HOST_PORT.
    Lisäksi käynnistetään kuuntelusäie.
    """
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
    """
    Yritetään yhdistää hostiin annetun IP:n avulla.
    """
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
    """
    Kuuntelee saapuvia TCP-viestejä ja puskee ne jonoonsa.
    """
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
    """Lähettää viestin TCP-yhteyden kautta."""
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
# Alkunäyttö (UI)
# -------------------------------------------------------
fontti = pygame.font.SysFont(None, 24)
iso_fontti = pygame.font.SysFont(None, 60)

def draw_main_menu(screen):
    theme = current_theme()
    screen.fill(theme["bg"])

    otsikko = fontti.render("Tervetuloa peliin!", True, theme["text"])
    screen.blit(otsikko, (LEVEYS // 2 - otsikko.get_width() // 2, 50))

    # HOST- ja JOIN-napit
    host_btn_rect = pygame.Rect(LEVEYS // 2 - 100, 150, 200, 50)
    join_btn_rect = pygame.Rect(LEVEYS // 2 - 100, 220, 200, 50)

    mx, my = pygame.mouse.get_pos()
    if host_btn_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], host_btn_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], host_btn_rect)
    pygame.draw.rect(screen, theme["border"], host_btn_rect, 2)
    host_label = fontti.render("HOST PELI", True, theme["text"])
    screen.blit(host_label, (host_btn_rect.centerx - host_label.get_width() // 2,
                             host_btn_rect.centery - host_label.get_height() // 2))

    if join_btn_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], join_btn_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], join_btn_rect)
    pygame.draw.rect(screen, theme["border"], join_btn_rect, 2)
    join_label = fontti.render("JOIN PELI", True, theme["text"])
    screen.blit(join_label, (join_btn_rect.centerx - join_label.get_width() // 2,
                             join_btn_rect.centery - join_label.get_height() // 2))

    # Toggle dark/light -nappi
    toggle_rect = pygame.Rect(10, 10, 100, 40)
    if toggle_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], toggle_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], toggle_rect)
    pygame.draw.rect(screen, theme["border"], toggle_rect, 2)
    mode_text = "Light Mode" if is_dark_mode else "Dark Mode"
    toggle_label = fontti.render(mode_text, True, theme["text"])
    screen.blit(toggle_label, (toggle_rect.centerx - toggle_label.get_width() // 2,
                               toggle_rect.centery - toggle_label.get_height() // 2))
    return host_btn_rect, join_btn_rect, toggle_rect

def draw_host_screen(screen):
    theme = current_theme()
    screen.fill(theme["bg"])
    t1 = fontti.render("Odotetaan pelaajaa liittymään...", True, theme["text"])
    screen.blit(t1, (50, 50))
    ipaddr = get_own_ip()
    t2 = fontti.render(f"IP: {ipaddr} (port {HOST_PORT})", True, theme["text"])
    screen.blit(t2, (50, 80))

def draw_join_screen(screen, join_ip, host_list_rects):
    theme = current_theme()
    screen.fill(theme["bg"])
    info_text = fontti.render("Anna hostin IP manuaalisesti:", True, theme["text"])
    screen.blit(info_text, (50, 50))
    ip_surf = fontti.render(join_ip, True, theme["text"])
    screen.blit(ip_surf, (50, 80))
    join_hint = fontti.render("Paina ENTER liittyäksesi", True, theme["text"])
    screen.blit(join_hint, (50, 110))

    # SCAN-nappi
    scan_button_rect = pygame.Rect(50, 200, 150, 40)
    mx, my = pygame.mouse.get_pos()
    if scan_button_rect.collidepoint((mx, my)):
        pygame.draw.rect(screen, theme["button_hover"], scan_button_rect)
    else:
        pygame.draw.rect(screen, theme["button_bg"], scan_button_rect)
    pygame.draw.rect(screen, theme["border"], scan_button_rect, 2)
    scan_label = fontti.render("SCAN LAN", True, theme["text"])
    screen.blit(scan_label, (scan_button_rect.centerx - scan_label.get_width() // 2,
                             scan_button_rect.centery - scan_label.get_height() // 2))

    # Näytetään löydetyt hostit
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
        screen.blit(ip_label, (r.x + 5, r.y + 5))
        y_offset += 40
    return scan_button_rect

# -------------------------------------------------------
# Pääohjelma
# -------------------------------------------------------
MAIN_MENU = 0
HOST_SCREEN = 1
JOIN_SCREEN = 2

state = MAIN_MENU
is_host = None
join_ip = ""
host_list_rects = []

def main():
    global state, is_host, join_ip, is_dark_mode, discovery_thread_running, discovery_thread, connected
    pygame.display.set_caption("Pelin alkunäyttö")
    screen = pygame.display.set_mode((LEVEYS, KORKEUS))
    clock = pygame.time.Clock()
    running = True

    while running:
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == MAIN_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    host_btn_rect, join_btn_rect, toggle_rect = draw_main_menu(screen)
                    if host_btn_rect.collidepoint((mx, my)):
                        is_host = True
                        # Käynnistetään host-säie
                        t = threading.Thread(target=host_thread)
                        t.daemon = True
                        t.start()
                        # Käynnistetään discovery_server, jotta LAN-scan
                        # saa vastauksen
                        discovery_thread_running = True
                        discovery_thread = threading.Thread(target=discovery_server)
                        discovery_thread.daemon = True
                        discovery_thread.start()
                        state = HOST_SCREEN
                    elif join_btn_rect.collidepoint((mx, my)):
                        is_host = False
                        state = JOIN_SCREEN
                    elif toggle_rect.collidepoint((mx, my)):
                        is_dark_mode = not is_dark_mode

            elif state == JOIN_SCREEN:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Yritetään yhdistää syötetyn IP:n avulla
                        t = threading.Thread(target=join_thread, args=(join_ip,))
                        t.daemon = True
                        t.start()
                    elif event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    else:
                        join_ip += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    # Tarkistetaan SCAN-nappi
                    scan_button_rect = pygame.Rect(50, 200, 150, 40)
                    if scan_button_rect.collidepoint((mx, my)):
                        t = threading.Thread(target=scan_for_hosts)
                        t.daemon = True
                        t.start()
                    # Tarkistetaan löytyneiden hostien listaa
                    for (r, ipaddr) in host_list_rects:
                        if r.collidepoint((mx, my)):
                            t = threading.Thread(target=join_thread, args=(ipaddr,))
                            t.daemon = True
                            t.start()

        # Piirretään kunkin tilan näyttö
        if state == MAIN_MENU:
            draw_main_menu(screen)
        elif state == HOST_SCREEN:
            draw_host_screen(screen)
        elif state == JOIN_SCREEN:
            draw_join_screen(screen, join_ip, host_list_rects)

        pygame.display.flip()

    discovery_thread_running = False
    if discovery_thread and discovery_thread.is_alive():
        discovery_thread.join()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
