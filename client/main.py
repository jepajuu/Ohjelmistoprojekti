from network import connect_to_server
from game import run_game
#pip install requests


def main():
    # Yritetään automaattisesti löytää palvelin UDP-broadcastilla
    # Käynnistetään pelisilmukka
    #game.py kutsuu network.py tiedoston connect_to_server()
    #jos serveriä ei ole käynnistetty pyytää palvelimen ip:tä
    run_game()

if __name__ == "__main__":
    main()