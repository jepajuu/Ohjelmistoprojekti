from flask import Flask, request
from flask_socketio import SocketIO, emit
import eventlet  # Optional: you can remove this import if not using its features
import socket
import threading

maks_pelaajat = 2

app = Flask(__name__)
# Switch to threading async mode for better compatibility on Windows
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

    players[sid] = ip  # Lisätään host myös pelaajiin

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

def get_my_ip():
    """Automatically grab the local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # This doesn't need to succeed in communicating with 8.8.8.8
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


#Socketio event pommin ampumiselle, lähettää
#koordinaatit ja broadcastaa takaisin kaikille pelaajille
@socketio.on('shoot_bomb')
def handle_shoot_bomb(data):
    """
    Vastaanottaa pommituksen koordinaatit (x, y)
    ja lähettää ne kaikille pelaajille.
    """
    x = data.get('x')
    y = data.get('y')
    print(f"Vastaanotettu pommitus koordinaatteihin {x}, {y}")
    emit('bomb_update', {'x': x, 'y': y}, broadcast=True)


# UDP discovery constants
UDP_DISCOVERY_PORT = 5557
DISCOVERY_REQUEST = "DISCOVER_SERVER_REQUEST"
DISCOVERY_RESPONSE = "DISCOVER_SERVER_RESPONSE"

def udp_discovery_listener():
    """Listens for UDP discovery requests and responds with the discovery response."""
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        udp_sock.bind(("", UDP_DISCOVERY_PORT))
        print(f"UDP discovery listener started on port {UDP_DISCOVERY_PORT}")
        while True:
            data, addr = udp_sock.recvfrom(1024)
            if data.decode() == DISCOVERY_REQUEST:
                udp_sock.sendto(DISCOVERY_RESPONSE.encode(), addr)
    except Exception as e:
        print("UDP discovery error:", e)
    finally:
        udp_sock.close()

if __name__ == "__main__":
    my_ip = get_my_ip()
    print(f"Server is running on IP: {my_ip}")
    
    # Start UDP discovery listener in a background thread
    discovery_thread = threading.Thread(target=udp_discovery_listener, daemon=True)
    discovery_thread.start()
    
    socketio.run(app, host="0.0.0.0", port=5555)