import sys
from pathlib import Path

# Lisää projektin juuri Pythonin hakupolkuun
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, request
from flask_socketio import SocketIO, emit
from server.game_logic import GameManager
from server.config import *
import threading
import socket

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
game_manager = GameManager()

# UDP discovery listener (sama kuin aiemmin)
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

# SocketIO tapahtumankäsittelijät
@socketio.on('connect')
def handle_connect():
    player_id = request.sid
    game_manager.add_player(player_id, request.remote_addr)
    emit('your_id', {'id': player_id})
    
    if game_manager.can_start():
        game_manager.start_game()
        emit('game_start', broadcast=True)

@socketio.on('set_ships')
def handle_set_ships(data):
    game_manager.set_ships(request.sid, data['ships'])
    if all(p.ships for p in game_manager.game.players.values()):
        emit('all_ships_ready', broadcast=True)

@socketio.on('shoot')
def handle_shoot(data):
    result = game_manager.process_shot(request.sid, data['x'], data['y'])
    emit('shot_result', result, broadcast=True)

def run_server():
    """Käynnistää palvelimen"""
    discovery_thread = threading.Thread(target=udp_discovery_listener, daemon=True)
    discovery_thread.start()
    print(f"Palvelin käynnistyy osoitteessa {SERVER_IP}:{DEFAULT_PORT}")
    socketio.run(app, host=SERVER_IP, port=DEFAULT_PORT)

if __name__ == "__main__":
    run_server()