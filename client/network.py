import socketio
import pygame
from game import own_bomb_data, opponent_bomb_data

sio = socketio.Client()

# Globaalit muuttujat
player_id = None
my_turn = False

pygame.init()
pygame.font.init()
GAME_STATE_UPDATE = pygame.USEREVENT + 1

#tapahtumankäsitttelijä uuden pelin laivanasetukselle
@sio.on('setup_ships')
def on_setup_ships(data):
    print("Aseta laivasi uudelleen")
    pygame.event.post(pygame.event.Event(GAME_STATE_UPDATE, {"new_state": "setup_ships"}))

@sio.on('waiting_for_players')
def on_waiting(data):
    print(data['message'])
#tapahtumankäsittelijä pelin tilan päivitykselle
# Tämä tapahtumankäsittelijä vastaanottaa pelin tilan päivityksen palvelimelta
@sio.on('game_state_update')
def on_game_state_update(data):
    new_state = data.get('new_state')
    print(f"Pelin tila muuttuu: {new_state}")
    event = pygame.event.Event(GAME_STATE_UPDATE, {"new_state": new_state})
    pygame.event.post(event)

#uuden pelin käsittelijä
# network.py (muutokset)
@sio.on('game_reset')
def on_game_reset(data):
    global my_turn
    print("Peli on resetoitu, valmiina uuteen peliin")
    # Nollaa pommitustiedot
    for x in range(10):
        for y in range(10):
            own_bomb_data[x][y] = 0
            opponent_bomb_data[x][y] = 0
    pygame.event.post(pygame.event.Event(GAME_STATE_UPDATE, {"new_state": "setup_ships"}))
@sio.on("player_joined")#kun uusi pelaaja liittynyt palvelimelle tullaan tänne
def on_player_joined(data):
    players_ready = data["players_connected"]#määrä montako pelaajaa liittynyt
    print(f"Pelaajia liittynyt: {players_ready}")
    if players_ready >= 2:
        pygame.event.post(pygame.event.Event(GAME_STATE_UPDATE, {"new_state": "setup_ships"}))

@sio.event
def connect():
    print("Yhdistetty palvelimeen.")

@sio.on('your_id')
def on_your_id(data):
    global player_id
    player_id = data['id']
    print("Oma tunniste:", player_id)

@sio.on('all_players_sid')#vastaanottaa tiedon palvelimelta kaikista pelaajista
def all_players_dict(data):
    players_all = data['message']
    print("Vastustajan tunniste:", players_all)




@sio.on('turn_change')
def on_turn_change(data):
    global my_turn
    my_turn = (data['current_turn'] == player_id)
    print(f"Vuoro vaihtui: {'SINUN VUOROSI' if my_turn else 'VASTUSTAJAN VUORO'}")
    event = pygame.event.Event(pygame.USEREVENT, {'custom_type': 'turn_update'})
    pygame.event.post(event)

@sio.on('game_start')
def on_game_start(data):
    print("Peli alkoi!")

# Kun palvelin vastaa tiedolla omasta pommituksesta
# Tämä käsittelee tuloksen siitä, osuiko pelaajan laukaus vastustajan ruudukkoon
@sio.on('bomb_result')
def on_bomb_result(data):
    x = data['x'] 
    y = data['y'] 
    hit = data['hit']  # Totuusarvo osuiko laukaus

    # Päivitetään vastustajan ruudukon tilanne: 2 = osuma, 1 = ohi
    opponent_bomb_data[x][y] = 2 if hit else 1

    # Tulostetaan tiedot konsoliin
    print(f"Oma laukaus: ({x},{y}) - {'OSUMA' if hit else 'OHI'}")

    # Laukaistaan pelissä tapahtuma, joka saa käyttöliittymän päivittämään ruudukot
    event = pygame.event.Event(pygame.USEREVENT, {'custom_type': 'bomb_update'})
    pygame.event.post(event)


# Kun palvelin ilmoittaa, että vastustaja ampui ja tulos on tiedossa
# Tämä kertoo, osuiko vastustajan laukaus pelaajan ruudukkoon
@sio.on('ship_hit')
def on_ship_hit(data):
    x = data['x']  
    y = data['y']  
    hit = data['hit']  # Totuusarvo osuiko laukaus

    # Päivitetään oma ruudukko: 2 = osuma, 1 = ohi
    own_bomb_data[x][y] = 2 if hit else 1

    # Tulostetaan konsoliin tieto vastustajan pommituksesta
    print(f"Vastustajan laukaus: ({x},{y}) - {'OSUMA' if hit else 'OHI'}")

    # Ilmoitetaan käyttöliittymälle, että pelitilanne pitää päivittää
    event = pygame.event.Event(pygame.USEREVENT, {'custom_type': 'bomb_update'})
    pygame.event.post(event)


@sio.on('not_your_turn')
def on_not_your_turn(data):
    print("Virhe:", data.get('message'))

def discover_server(timeout=5):
    import socket
    UDP_DISCOVERY_PORT = 5557
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
    global sio
    discovered_ip = discover_server()
    if discovered_ip:
        server_ip = discovered_ip
    else:
        server_ip = input("Syötä palvelimen IP: ")
    SERVER_PORT = 5555
    
    if sio.connected:
        print("Yhteys on jo olemassa, ei yhdistetä uudelleen")
        return
    
    try:
        print(f"Yhdistetään palvelimeen {server_ip}:{SERVER_PORT}...")
        sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        print("Yhteys palvelimeen onnistui!")
    except Exception as e:
        print("Virhe yhdistettäessä palvelimeen:", e)
        sio = socketio.Client()
        try:
            sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        except Exception as e2:
            print("Uudelleenyritys epäonnistui:", e2)