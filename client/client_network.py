import socketio
import shared.models as models
from server.config import SERVER_IP, DEFAULT_PORT
from shared.models import Ship

sio = socketio.Client()
game_state = None  # Pelitilaan viittaus; voit tehdä oman GameUI:n tai vastaavan

def connect_to_server(ip=SERVER_IP):
    try:
        sio.connect(f"http://{ip}:{DEFAULT_PORT}")
        print("Yhteys palvelimeen onnistui.")
    except Exception as e:
        print("Connection failed:", e)

@sio.on('your_id')
def on_id_received(data):
    global game_state
    if game_state:
        game_state.player_id = data['id']

@sio.on('game_start')
def on_game_start(data):
    global game_state
    if game_state:
        game_state.phase = "setup_ships"
