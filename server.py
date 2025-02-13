from flask import Flask, request
from flask_socketio import SocketIO, emit
import eventlet  # Optional: you can remove this import if not using its features

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

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5555)