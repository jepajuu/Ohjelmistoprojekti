from flask import Flask, request
from flask_socketio import SocketIO, emit
import threading
import socket

maks_pelaajat = 2

# Pelaajien tiedot: socket-id:t ja vuorojärjestys
players = {}         # dictionary jossa liittyneiden pelaajien {sid: ip} 
player_turns = []    # Lista socket-id:itä
current_turn_index = 0

# Uusi sanakirja pelaajien laivoille
player_boards = {}

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

@app.route('/')
def index():
    return "Peli-serveri toimii!"

#handle_reset -tapahtumankäsittelijä
@socketio.on('reset_game')
def handle_reset():
    global players, player_turns, current_turn_index, player_boards
    # Pidetään pelaajat, mutta nollataan muut tiedot
    player_turns = list(players.keys())
    current_turn_index = 0
    player_boards = {}
    print("Peli resetoidtu, valmiina uuteen peliin")
    emit('game_reset', {}, broadcast=True)
    # Lähetä vuoro ensimmäiselle pelaajalle
    emit('turn_change', {'current_turn': player_turns[current_turn_index]}, broadcast=True)
    # Lähetä tieto pelitilan päivityksestä
    emit('game_state_update', {'new_state': 'setup_ships'}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    global current_turn_index
    sid = request.sid
    players[sid] = request.remote_addr
    player_turns.append(sid)
    emit('your_id', {'id': sid})
    print(f"Pelaaja {sid} liittyi. Pelaajia yhteensä: {len(players)}")
    
    # Lähetä pelaajalle tieto siitä, onko peli käynnissä vai odottamassa toista pelaajaa
    if len(players) < maks_pelaajat:
        emit('waiting_for_players', {'message': 'Odotetaan toista pelaajaa...'})
    else:
        # Lähetä kaikille pelaajille tieto pelin alkamisesta
        emit('player_joined', {"players_connected": len(players)}, broadcast=True)
        emit('all_players_sid', {"message": players}, broadcast=True)
        # Älä lähetä vielä game_start -viestiä, vaan odota että molemmat asettavat laivat
        emit('setup_ships', {}, broadcast=True)

@socketio.on('ships_ready')
def handle_ships_ready(data):
    sid = request.sid
    print(f"Pelaaja {sid} on valmis")
    
    if 'ready_players' not in players:
        players['ready_players'] = set()
    
    players['ready_players'].add(sid)
    
    if len(players['ready_players']) == maks_pelaajat:
        print("Kaikki pelaajat valmiita - peli alkaa!")
        current_turn_index = 0
        emit('game_start', {}, broadcast=True)
        emit('turn_change', {'current_turn': player_turns[current_turn_index]}, broadcast=True)
        emit('game_state_update', {'new_state': 'playing'}, broadcast=True)
        del players['ready_players']

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in players:
        players.pop(sid)
    if sid in player_boards:
        player_boards.pop(sid)
    if sid in player_turns:
        player_turns.remove(sid)
    print(f"Pelaaja {sid} poistui.")
    emit('player_left', {"id": sid}, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    print(f"Vastaanotettu viesti: {data['message']}")
    emit('receive_message', data, broadcast=True)

# Uusi tapahtumankäsittelijä laivojen asettamiselle
@socketio.on('set_ships')
def handle_set_ships(data):
    ships = data.get('ships', [])
    player_boards[request.sid] = ships
    print(f"Pelaajan {request.sid} laivat asetettu: {ships}")

# Muokattu ampumistapahtuma
# Muokkaa shoot_bomb -käsittelijää lähettämään erilliset tapahtumat
# Kuunnellaan 'shoot_bomb'-tapahtumaa, joka tulee pelaajalta, kun hän yrittää ampua pommin johonkin ruutuun
@socketio.on('shoot_bomb')
def handle_shoot_bomb(data):
    global current_turn_index

    # Haetaan ampujan socket-id (SID)
    shooter_sid = request.sid
    print(f"Pelaaja {shooter_sid} ampuu ruutuun ({data['x']},{data['y']})")

    # Tarkistetaan, onko tällä pelaajalla vuoro
    if shooter_sid != player_turns[current_turn_index]:
        print("Ei vuoroa!")
        # Lähetetään takaisin viesti, että ei ole tämän pelaajan vuoro
        emit('not_your_turn', {"message": "Odota vuoroasi!"})
        return

    # Haetaan ammutun ruudun koordinaatit
    x = data.get('x')
    y = data.get('y')

    # Selvitetään vastustajan SID (pelaaja joka ei ole nyt ampuja)
    opponent_sid = next((sid for sid in player_turns if sid != shooter_sid), None)

    hit = False  # Oletuksena ei osumaa

    # Jos vastustajalla on laivataulu
    if opponent_sid in player_boards:
        # Tarkistetaan, onko kyseinen koordinaatti vastustajan laivalistassa (osuma)
        hit = [x, y] in player_boards[opponent_sid]
        if hit:
            # Poistetaan osuttu ruutu vastustajan laivoista (upotus logiikka)
            player_boards[opponent_sid].remove([x, y])
            print("OSUMA!")
        else:
            print("OHI!")

    # Lähetetään tulos ampujalle (oman ruudukon päivittämiseksi)
    emit('bomb_result', {'x': x, 'y': y, 'hit': hit}, room=shooter_sid)

    # Lähetetään tieto myös vastustajalle (omien laivojen tilan päivittämiseksi)
    emit('ship_hit', {'x': x, 'y': y, 'hit': hit}, room=opponent_sid)

    # Jos ei osuttu, vuoro vaihtuu
    if not hit:
        current_turn_index = (current_turn_index + 1) % len(player_turns)
        print(f"Vuoro vaihtuu pelaajalle {player_turns[current_turn_index]}")

    # Lähetetään uusi vuorotilanne kaikille pelaajille
    emit('turn_change', {'current_turn': player_turns[current_turn_index]}, broadcast=True)


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

if __name__ == "__main__":
    run_server()