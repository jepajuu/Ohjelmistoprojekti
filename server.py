from flask import Flask, request
from flask_socketio import SocketIO, emit
import eventlet  # Optional: voit poistaa tämän, jos et käytä sen ominaisuuksia
import socket
import threading

maks_pelaajat = 2

app = Flask(__name__)
# Käytetään threading async modea Windowsille
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

players = {}  # Tallentaa pelaajien yhteydet

@app.route('/')
def index():
    return "Peli-serveri toimii!"

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    ip = request.remote_addr
    print(f"Uusi pelaaja liittyi: {ip}, ID: {sid}")
    players[sid] = ip
    print(f"Pelaajia liittynyt yhteensä: {len(players)}")
    emit('player_joined', {"players_connected": len(players)}, broadcast=True)
    if len(players) == maks_pelaajat:
        print("Peli alkaa, molemmat pelaajat ovat liittyneet")
        emit('game_start', {"message": "Peli alkaa"}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    ip = players.pop(request.sid, "tuntematon")
    print(f"Pelaaja {ip} poistui")
    emit('player_left', {"ip": ip}, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    print(f"Vastaanotettu viesti: {data['message']}")
    emit('receive_message', data, broadcast=True)

@socketio.on('bomb_shot')
def handle_bomb_shot(data):
    x = data.get("x")
    y = data.get("y")
    print(f"Received bomb shot at ({x}, {y}) from {request.sid}")
    emit('bomb_shot', data, broadcast=True)

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

UDP_DISCOVERY_PORT = 5557
DISCOVERY_REQUEST = "DISCOVER_SERVER_REQUEST"
DISCOVERY_RESPONSE = "DISCOVER_SERVER_RESPONSE"

def udp_discovery_listener():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        udp_sock.bind(("", UDP_DISCOVERY_PORT))
        print(f"UDP discovery listener started on port {UDP_DISCOVERY_PORT}")
        while True:
            data, addr = udp_sock.recvfrom(1024)
            if data.decode().strip() == DISCOVERY_REQUEST:
                udp_sock.sendto(DISCOVERY_RESPONSE.encode(), addr)
    except Exception as e:
        print("UDP discovery error:", e)
    finally:
        udp_sock.close()

if __name__ == "__main__":
    my_ip = get_my_ip()
    print(f"Server is running on IP: {my_ip}")
    discovery_thread = threading.Thread(target=udp_discovery_listener, daemon=True)
    discovery_thread.start()
    socketio.run(app, host="0.0.0.0", port=5555)