# client/main.py
from network import connect_to_server
from game import run_game

def main():
    # Yritetään automaattisesti löytää palvelin UDP-broadcastilla
    connect_to_server()
    # Käynnistetään pelisilmukka
    run_game()

if __name__ == "__main__":
    main()
