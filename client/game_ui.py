import pygame
from server.config import SCREEN_WIDTH, SCREEN_HEIGHT
from client.client_network import connect_to_server
from shared.models import Ship
from shared.constants import SHIP_TEMPLATES

class GameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.phase = "menu"  # menu, setup, game, end
        self.ships = self.create_ships()
        
    def create_ships(self):
        return [Ship(**template) for template in SHIP_TEMPLATES]
    
    def draw_board(self):
        # Piirrä ruudukko ja laivat haluamallasi tavalla
        self.screen.fill((0, 0, 0))
    
    def handle_click(self, position):
        # Klikkaustapahtumien käsittely
        pass

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_click(event.pos)
        return True
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.draw_board()
            pygame.display.flip()

def main():
    ui = GameUI()
    connect_to_server()
    ui.run()

if __name__ == "__main__":
    main()
