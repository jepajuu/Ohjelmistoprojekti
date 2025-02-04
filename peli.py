import pygame
import sys
 
# Asetukset
WIDTH, HEIGHT = 500, 500
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
 
# Pygame alustaminen
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Laivanupotus")
 
# Fontit
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 28)
 
def draw_text(text, x, y, color=BLACK, font=font):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))
 
def input_box():
    input_active = True
    user_text = ""
 
    while input_active:
        screen.fill(WHITE)
        draw_text("Enter Server IP:", 150, 150, BLACK)
        pygame.draw.rect(screen, BLACK, (150, 200, 200, 40), 2)
        
        text_surface = font.render(user_text, True, BLACK)
        screen.blit(text_surface, (160, 210))
 
        pygame.display.flip()
 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return user_text
                elif event.key == pygame.K_BACKSPACE:
                    user_text = user_text[:-1]
                else:
                    user_text += event.unicode
 
def show_menu():
    running = True
 
    while running:
        screen.fill(WHITE)
        draw_text("Laivanupotus", 180, 100, BLUE, font)
 
        # Piirretään napit
        pygame.draw.rect(screen, GRAY, (150, 200, 200, 50))
        pygame.draw.rect(screen, GRAY, (150, 300, 200, 50))
 
        draw_text("Host", 210, 215, BLACK, small_font)
        draw_text("Join", 210, 315, BLACK, small_font)
 
        pygame.display.flip()
 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
 
                if 150 <= mx <= 350 and 200 <= my <= 250:  # Host
                    return "host"
                elif 150 <= mx <= 350 and 300 <= my <= 350:  # Join
                    ip = input_box()
                    return "join", ip
 
# Testataan alkunäyttö
if __name__ == "__main__":
    choice = show_menu()
    print("Valinta:", choice)