# server/network.py
from flask import Flask, request
from flask_socketio import SocketIO, emit
import threading
import socket

maks_pelaajat = 2

# Pelaajien tiedot: pelaajien socket-id:t ja vuorojärjestys
players = {}         # Esim. {sid: ip}
player_turns = []    # Lista socket-id:itä
current_turn_index = 0

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

@app.route('/')
def index():
    return "Peli-serveri toimii!"

@socketio.on('connect')
def handle_connect():
    global current_turn_index
    sid = request.sid
    players[sid] = request.remote_addr
    player_turns.append(sid)
    # Lähetetään asiakkaalle sen oma tunniste
    emit('your_id', {'id': sid})
    print(f"Pelaaja {sid} liittyi. Pelaajia yhteensä: {len(players)}")
    
    # Ilmoitetaan pelaajien määrä kaikille
    emit('player_joined', {"players_connected": len(players)}, broadcast=True)
    
    if len(players) == maks_pelaajat:
        print("Peli alkaa, molemmat pelaajat ovat liittyneet")
        # Aloitetaan peli: ensimmäisen pelaajan vuoro
        emit('turn_change', {'current_turn': player_turns[current_turn_index]}, broadcast=True)
        emit('game_start', {"message": "Peli alkaa"}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in players:
        players.pop(sid)
    print(f"Pelaaja {sid} poistui.")
    emit('player_left', {"id": sid}, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    print(f"Vastaanotettu viesti: {data['message']}")
    emit('receive_message', data, broadcast=True)

# Socketio-event ampumiselle
@socketio.on('shoot_bomb')
def handle_shoot_bomb(data):
    global current_turn_index
    # Varmistetaan, että ampuva pelaaja on vuorossa
    if request.sid != player_turns[current_turn_index]:
        print("Ei sinun vuorosi!")
        emit('not_your_turn', {"message": "Odota vuoroasi!"})
        return

    x = data.get('x')
    y = data.get('y')
    print(f"Pelaaja {request.sid} ampui koordinaatteihin ({x}, {y})")
    emit('bomb_update', {'x': x, 'y': y}, broadcast=True)
    
    # Vuoron vaihto
    current_turn_index = (current_turn_index + 1) % len(player_turns)
    new_turn_sid = player_turns[current_turn_index]
    emit('turn_change', {'current_turn': new_turn_sid}, broadcast=True)
    print("Uusi vuoro:", new_turn_sid)

def udp_discovery_listener():
    UDP_DISCOVERY_PORT = 5557
    DISCOVERY_REQUEST = "DISCOVER_SERVER_REQUEST"
    DISCOVERY_RESPONSE = "DISCOVER_SERVER_RESPONSE"
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        udp_sock.bind(("", UDP_DISCOVERY_PORT))
        print(f"UDP discovery listener käynnistetty portissa {UDP_DISCOVERY_PORT}")
        while True:
            data, addr = udp_sock.recvfrom(1024)
            if data.decode() == DISCOVERY_REQUEST:
                udp_sock.sendto(DISCOVERY_RESPONSE.encode(), addr)
    except Exception as e:
        print("UDP discovery error:", e)
    finally:
        udp_sock.close()

def get_my_ip():
    """Hakee paikallisen IP-osoitteen."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def run_server():
    # Käynnistetään UDP discovery taustalla
    discovery_thread = threading.Thread(target=udp_discovery_listener, daemon=True)
    discovery_thread.start()
    ip = get_my_ip()
    print(f"Server toimii IP-osoitteessa: {ip}")
    socketio.run(app, host="0.0.0.0", port=5555)
