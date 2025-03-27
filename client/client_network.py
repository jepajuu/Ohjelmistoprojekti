import socketio
from .config import *
from shared.models import Ship

sio = socketio.Client()
game_state = None  # Viittaus pelitilaan

def connect_to_server(ip=SERVER_IP):
    try:
        sio.connect(f"http://{ip}:{DEFAULT_PORT}")
    except Exception as e:
        print("Connection failed:", e)

@sio.on('your_id')
def on_id_received(data):
    game_state.player_id = data['id']

@sio.on('game_start')
def on_game_start(data):
    game_state.phase = "setup_ships"