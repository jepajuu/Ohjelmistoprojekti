from flask import Flask, request
from flask_socketio import SocketIO, emit
import eventlet  # Optional: you can remove this import if not using its features
import socket

app = Flask(__name__)
# Switch to threading async mode for better compatibility on Windows
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

players = {}  # Tallentaa pelaajien yhteydet

@app.route('/')
def index():
    return "Peli-serveri toimii!"

@socketio.on('connect')
def handle_connect():
    ip = request.remote_addr
    print(f"Uusi pelaaja liittyi: {ip}")
    players[request.sid] = ip
    emit('player_joined', {"ip": ip}, broadcast=True)

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

if __name__ == "__main__":
    my_ip = get_my_ip()
    print(f"Server is running on IP: {my_ip}")
    socketio.run(app, host="0.0.0.0", port=5555)