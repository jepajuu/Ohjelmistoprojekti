import socketio
import pygame
from game import own_bomb_data, opponent_bomb_data

import game

sio = socketio.Client()

# Globaalit muuttujat
player_id = None
my_turn = False

import pygame
pygame.init()
pygame.font.init()
GAME_STATE_UPDATE = pygame.USEREVENT + 1

@sio.on("player_joined")
def on_player_joined(data):
    players_ready = data["players_connected"]
    print(f"Pelaajia liittynyt: {players_ready}")
    if players_ready >= 2:
        # Postitetaan custom-eventti, jotta pelisilmukka tietää tilan vaihdoksen
        pygame.event.post(pygame.event.Event(GAME_STATE_UPDATE, {"new_state": "setup_ships"}))

@sio.event
def connect():
    print("Yhdistetty palvelimeen.")

@sio.on('your_id')
def on_your_id(data):
    global player_id
    player_id = data['id']
    print("Oma tunniste:", player_id)


@sio.on('turn_change')
def on_turn_change(data):
    global my_turn
    my_turn = (data['current_turn'] == player_id)
    print(f"Vuoro vaihtui: {'SINUN VUOROSI' if my_turn else 'VASTUSTAJAN VUORO'}")
    pygame.event.post(pygame.event.Event(pygame.USEREVENT, {'type': 'turn_update'}))

@sio.on('game_start')
def on_game_start(data):
    print(data['message'])

# Lisää uudet tapahtumankäsittelijät
@sio.on('bomb_result')
def on_bomb_result(data):
    x = data['x']
    y = data['y']
    hit = data['hit']
    opponent_bomb_data[x][y] = 2 if hit else 1
    print(f"Oma laukaus: ({x},{y}) - {'OSUMA' if hit else 'OHI'}")
    pygame.event.post(pygame.event.Event(pygame.USEREVENT, {'type': 'bomb_update'}))

@sio.on('bomb_result')
def on_bomb_result(data):
    x = data['x']
    y = data['y']
    hit = data['hit']
    opponent_bomb_data[x][y] = 2 if hit else 1
    print(f"Oma laukaus: ({x},{y}) - {'OSUMA' if hit else 'OHI'}")
    pygame.event.post(pygame.event.Event(pygame.USEREVENT, {'type': 'bomb_update'}))
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
    
    # Tarkista onko yhteys jo olemassa
    if sio.connected:
        print("Yhteys on jo olemassa, ei yhdistetä uudelleen")
        return
    
    try:
        print(f"Yhdistetään palvelimeen {server_ip}:{SERVER_PORT}...")
        sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        print("Yhteys palvelimeen onnistui!")
    except Exception as e:
        print("Virhe yhdistettäessä palvelimeen:", e)
        # Yritä uudelleen luomalla uusi SocketIO-olio
        sio = socketio.Client()
        try:
            sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        except Exception as e2:
            print("Uudelleenyritys epäonnistui:", e2)