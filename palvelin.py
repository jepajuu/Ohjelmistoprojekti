from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Sallii verkkoyhteydet

players = []  # Lista liittyneistä pelaajista

@app.route('/')
def home():
    return "Flask-palvelin toimii!"  # Nyt tämä toimii!

@socketio.on('connect')
def on_connect():
    if len(players) < 2:
        players.append(request.sid)
        emit('player_id', {'player_id': len(players)}, room=request.sid)
    else:
        emit('server_full', {'message': 'Peli on täynnä'}, room=request.sid)

@socketio.on('shoot')
def handle_shoot(data):
    print(f"Koordinaatit vastaanotettu: {data}")
    emit('shot_fired', data, broadcast=True, include_self=False)  # Lähettää muille pelaajille

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
