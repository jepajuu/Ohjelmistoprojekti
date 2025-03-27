import pygame
from .client_network import *
from .config import *
from shared.models import Ship

class GameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.phase = "menu"  # menu, setup, game, end
        self.ships = self.create_ships()
        
    def create_ships(self):
        return [Ship(**template) for template in SHIP_TEMPLATES]
    
    def draw_board(self):
        # Piirrä ruudukko ja laivat
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

if __name__ == "__main__":
    ui = GameUI()
    connect_to_server()
    ui.run()