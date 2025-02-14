import pygame
import sys
import socket
import socketio
import time

pygame.init()
pygame.font.init()

LEVEYS, KORKEUS = 800, 600
#pip install "python-socketio"

# Käytetään socket.io-clientia
sio = socketio.Client()

UDP_DISCOVERY_PORT = 5557  # UDP-löytymispalvelu

def discover_server(timeout=5):
    """Etsii palvelimen lähettämällä UDP-broadcastin."""
    discovery_message = b"DISCOVER_SERVER_REQUEST"
    expected_response = "DISCOVER_SERVER_RESPONSE"
    server_ip = None
    
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(timeout)
    
    try:
        udp_sock.sendto(discovery_message, ("<broadcast>", UDP_DISCOVERY_PORT))
        data, addr = udp_sock.recvfrom(1024)
        if data.decode() == expected_response:
            server_ip = addr[0]
            print(f"Palvelin löytyi IP:stä {server_ip}")
    except socket.timeout:
        print("Palvelimen löytyminen aikakatkaistiin.")
    except Exception as e:
        print("Virhe palvelimen etsinnässä:", e)
    finally:
        udp_sock.close()
    
    return server_ip

def connect_to_server():
    discovered_ip = discover_server()
    if discovered_ip:
        server_ip = discovered_ip
    else:
        server_ip = input("Syötä palvelimen IP: ")
    
    SERVER_PORT = 5555
    try:
        sio.connect(f"http://{server_ip}:{SERVER_PORT}")
        print("Yhteys palvelimeen onnistui!")
    except Exception as e:
        print("Virhe yhdistettäessä palvelimeen:", e)

# Pygame UI
fontti = pygame.font.SysFont(None, 50)
screen = pygame.display.set_mode((LEVEYS, KORKEUS))
pygame.display.set_caption("Laivanupotus")

host_rect = pygame.Rect(LEVEYS // 2 - 160, 300, 150, 50)#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
join_rect = pygame.Rect(LEVEYS // 2 + 90, 300, 150, 50)
laivojen_asetus_rect = pygame.Rect(((LEVEYS/2)-150), 400, 300, 50)

#2d lista 10*10 laivoille  pelikenttä 0=ei laivaa 1=on laiva
laivat=[[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0]]
#arvot voi olla 0-9   [A-J, 1-10]
lentotukialus=[[2,2],[2,3],[2,4],[2,5],[2,6]]#x y koordinaatit alustetaan -1
taistelulaiva=[[9,0],[9,1],[9,2],[9,3]]#alustus -1 kun asetettu != -1
risteilija1=[[9,9],[8,9],[7,9]]#3 ruutua risteilija

def piirra_ruudukko():
    screen.fill((255, 255, 255))#tyhjää ikkuna
    for i in range(11):#ruudukon piirto
        pygame.draw.line(screen,(0, 0, 0), [(LEVEYS/11)*i,0], [(LEVEYS/11)*i,KORKEUS])#pystyviivat
        pygame.draw.line(screen,(0, 0, 0), [0,(KORKEUS/11)*i], [LEVEYS,(KORKEUS/11)*i])#vaakaviivat
        if (i>0):
            number_text = fontti.render(str(i), True, (0, 0, 0))#numerot 1-10
            screen.blit(number_text, (((LEVEYS/11)*0.1), (((KORKEUS/11)*i)+5)))
            aakkonen_text = fontti.render(str(chr(i+64)), True, (0, 0, 0))#aakoset A-J chr(asciin numero)
            screen.blit(aakkonen_text, ((((LEVEYS/11)*i)+5),((KORKEUS/11)*0.1) ))
    pygame.display.flip()

def piirra_laivat():#myös asettaa laivat 2d listaan
    if(lentotukialus[0][0] != -1):
        for i in range(len(lentotukialus)):#kiertää lentotukialuksen pituuden verran i=0,1,2,3,4
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[lentotukialus[i][0]][lentotukialus[i][1]]=1 #lentotukialuksen[i][0] on x ja [i][1] on y
    
    if(taistelulaiva[0][0] != -1):
        for i in range(len(taistelulaiva)):#kiertää lentotukialuksen pituuden verran i=0,1,2,3,4
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[taistelulaiva[i][0]][taistelulaiva[i][1]]=1 #lentotukialuksen[i][0] on x ja [i][1] on y
    
    if(risteilija1[0][0] != -1):
        for i in range(len(risteilija1)):#kiertää lentotukialuksen pituuden verran i=0,1,2,3,4
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[risteilija1[i][0]][risteilija1[i][1]]=1 #lentotukialuksen[i][0] on x ja [i][1] on y
    
    for x in range(len(laivat)):#piirtää laivat laivat 2d taulukosta jos 1
        print(x)
        for y in range(len(laivat[x])):
            if(laivat[x][y]==1):
                cell_rect = pygame.Rect((((LEVEYS/11)*x)+(LEVEYS/11)), (((KORKEUS/11)*y)+(KORKEUS/11)), (LEVEYS/10.9), (KORKEUS/10.9))#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
                pygame.draw.rect(screen, (50, 50, 200), cell_rect)
                pygame.display.flip()


def aseta_laivat():
    piirra_ruudukko()
    piirra_laivat()
    time.sleep(5)
    #tähän laivojen asetus 
    #aseta lentotukialus 5ruutua
    #while True:
    #    for event in pygame.event.get():
    #        if event.type == pygame.KEYDOWN:
    #            print(event.key)
    #            time.sleep(1)
            #
            #
            #
            #
            #
            #
            #


            

    pygame.display.flip()
    time.sleep(2)
    

def draw_start_screen():
    screen.fill((0, 0, 0))
    otsikko = fontti.render("Laivanupotus peli :D", True, (255, 255, 255))
    pygame.draw.rect(screen, (50, 50, 200), host_rect)
    pygame.draw.rect(screen, (50, 200, 50), join_rect)
    pygame.draw.rect(screen, (50, 200, 50), laivojen_asetus_rect)#alusta,väri,neliö
    
    host_text = fontti.render("HOST", True, (255, 255, 255))
    join_text = fontti.render("JOIN", True, (255, 255, 255))
    laivojen_asetus_text = fontti.render("ASETA LAIVAT", True, (255, 255, 255))
    
    screen.blit(otsikko, (LEVEYS // 2 - otsikko.get_width() // 2, 150))
    screen.blit(host_text, (host_rect.x + 35, host_rect.y + 10))
    screen.blit(join_text, (join_rect.x + 35, join_rect.y + 10))
    screen.blit(laivojen_asetus_text, (laivojen_asetus_rect.x + 35, laivojen_asetus_rect.y + 10))
    
    pygame.display.flip()

def main():
    clock = pygame.time.Clock()
    running = True
    start_screen = True
    
    while running:
        clock.tick(30)
        
        if start_screen:
            draw_start_screen()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:  # Host
                        print("Hosting game...")
                        start_screen = False  # Tässä voisi alkaa hostauksen käsittely
                    elif event.key == pygame.K_j:  # Join
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False  # Tässä voisi alkaa liittymisen käsittely
                    elif event.key == pygame.K_a:  # aseta laivat
                        print("laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()
                        
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if host_rect.collidepoint(event.pos):
                        print("Hosting game...")
                        start_screen = False
                    elif join_rect.collidepoint(event.pos):
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False
                    elif laivojen_asetus_rect.collidepoint(event.pos):
                        print("laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()
        else:
            screen.fill((0, 50, 0))
            pygame.display.flip()
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
