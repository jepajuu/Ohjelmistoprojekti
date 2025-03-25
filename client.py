import pygame
import sys
import socket
import socketio
import time
import copy#tämä tarvitaan että voi tehdä sisäkkäisille listoille copyn

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

@sio.on("player_joined")
def on_player_joined(data):
    global players_ready, game_state
    players_ready = data["players_connected"]
    print(f"Pelaajia liittynyt: {players_ready}")

    if players_ready >= 2:
        game_state = "setup_ships"  # vaihtaa laivojen asetus tilaan
        aseta_laivat()

@sio.on("game_start")
def on_game_start(data):
    global game_state
    print(data["message"])  # tulostaa Peli alkaa

    game_state = "setup_ships"  # siirtyy laivojen asettamiseen
    print("Pelimuoto setup_ships")

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
screen = pygame.display.set_mode((LEVEYS, KORKEUS),pygame.RESIZABLE)
pygame.display.set_caption("Laivanupotus")

host_rect = pygame.Rect(LEVEYS // 2 - 160, 300, 150, 50)#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
join_rect = pygame.Rect(LEVEYS // 2 + 5, 300, 150, 50)
laivojen_asetus_rect = pygame.Rect(((LEVEYS/2)-150), 400, 300, 50)

#2d lista 10*10 laivoille  pelikenttä 0=ei laivaa 1=on laiva
laivat=[[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0]]
#2d lista 10*10 pommituksille 0=ei pommitettu 1=pommitettu
bomb_data=[[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],
[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0,0,0]]
#arvot voi olla 0-9   [A-J, 1-10]
lentotukialus=[[-1,-1],[2,3],[2,4],[2,5],[2,6]]#x y koordinaatit alustetaan -1
lentotukialusCopy=[[-1,-1],[2,3],[2,4],[2,5],[2,6]]#kopiot Joita ei piirretä 2d listaan
taistelulaiva=[[-1,-1],[9,1],[9,2],[9,3]]#alustus -1 kun asetettu != -1
taistelulaivaCopy=[[-1,-1],[9,1],[9,2],[9,3]]
risteilija1=[[-1,-1],[1,2],[1,3]]#3 ruutua risteilija
risteilija1Copy=[[-1,-1],[1,2],[1,3]]
risteilija2=[[-1,-1],[1,6],[2,6]]#3
risteilija2Copy=[[-1,-1],[1,6],[2,6]]#3
havittaja=[[-1,-1],[-1,-1]]
havittajaCopy=[[-1,-1],[-1,-1]]
sukellusvene=[[-1,-1]]
sukellusveneCopy=[[-1,-1]]

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
    global laivat
    for i in range(len(laivat)):#asettaa nollaksi laivat2d
        for r in range(len(laivat[i])):
            laivat[i][r]=0

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

    if(risteilija2[0][0] != -1):
        for i in range(len(risteilija2)):#kiertää lentotukialuksen pituuden verran i=0,1,2,3,4
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[risteilija2[i][0]][risteilija2[i][1]]=1 #lentotukialuksen[i][0] on x ja [i][1] on y
    
    if(havittaja[0][0] != -1):
        for i in range(len(havittaja)):#kiertää lentotukialuksen pituuden verran i=0,1,2,3,4
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[havittaja[i][0]][havittaja[i][1]]=1 #lentotukialuksen[i][0] on x ja [i][1] on y

    if(sukellusvene[0][0] != -1):
        for i in range(len(sukellusvene)):#kiertää lentotukialuksen pituuden verran i=0,1,2,3,4
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[sukellusvene[i][0]][sukellusvene[i][1]]=1 #lentotukialuksen[i][0] on x ja [i][1] on y

    for x in range(len(laivat)):#piirtää laivat laivat 2d taulukosta jos 1
        #print(x)
        for y in range(len(laivat[x])):
            if(laivat[x][y]==1):
                cell_rect = pygame.Rect((((LEVEYS/11)*x)+(LEVEYS/11)), (((KORKEUS/11)*y)+(KORKEUS/11)), (LEVEYS/10.9), (KORKEUS/10.9))#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
                pygame.draw.rect(screen, (50, 50, 200), cell_rect)
                pygame.display.flip()

def update_bomb_data(x, y):
    if bomb_data[x][y]==0:
        bomb_data[x][y]=1  # Merkkaa solun pommitetuksi
        if laivat[x][y]==1:
            print("Osuma!")
        else:
            print("Ohitus!")

def piirra_pommitukset():
    for x in range(10):
        for y in range(10):
            if bomb_data[x][y]==1:
                cell_x = ((LEVEYS/11)*x)+(LEVEYS/11)
                cell_y = ((KORKEUS/11)*y)+(KORKEUS/11)
                pygame.draw.circle(screen, (255, 0, 0),
                                   (int(cell_x+(LEVEYS/10.9)/2),int(cell_y+(KORKEUS/10.9)/2)),
                                   int(LEVEYS/30))
    pygame.display.flip()

def aseta_laivat():
    piirra_ruudukko()
    piirra_laivat()
   
    #for i in range(len(taistelulaiva)):
    #    taistelulaivaCopy[i][0]=taistelulaiva[i][0]
    global taistelulaiva
    global taistelulaivaCopy
    taistelulaivaCopy=copy.deepcopy(taistelulaiva)#deepcopy kopioi sisäkkäisetkin listat
    taistelulaiva[0][0]=-1
    taistelulaiva=aseta_yksi_laiva(taistelulaivaCopy)
    piirra_ruudukko()
    piirra_laivat()

    global lentotukialus
    global lentotukialusCopy
    lentotukialusCopy=copy.deepcopy(lentotukialus)
    lentotukialus[0][0]=-1
    lentotukialus=aseta_yksi_laiva(lentotukialusCopy)
    piirra_ruudukko()
    piirra_laivat()

    global risteilija1
    global risteilija1Copy
    risteilija1Copy=copy.deepcopy(risteilija1)
    risteilija1[0][0]=-1
    risteilija1=aseta_yksi_laiva(risteilija1Copy)
    piirra_ruudukko()
    piirra_laivat()

    global risteilija2
    global risteilija2Copy
    risteilija2Copy=copy.deepcopy(risteilija2)
    risteilija2[0][0]=-1
    risteilija2=aseta_yksi_laiva(risteilija2Copy)
    piirra_ruudukko()
    piirra_laivat()

    global havittaja
    global havittajaCopy
    havittajaCopy=copy.deepcopy(havittaja)
    havittaja[0][0]=-1
    havittaja=aseta_yksi_laiva(havittajaCopy)
    piirra_ruudukko()
    piirra_laivat()

    global sukellusvene
    global sukellusveneCopy
    sukellusveneCopy=copy.deepcopy(sukellusvene)
    sukellusvene[0][0]=-1
    sukellusvene=aseta_yksi_laiva(sukellusveneCopy)
    piirra_ruudukko()
    piirra_laivat()
 
    pygame.display.flip()
    time.sleep(2)

#lähinnä aseta yksi laiva funktiota varten
#piirtää laivan mutta ei lisää mitään laivat 2dListaan
def piirra_yksi_laiva(laiva_yksi,vari_yksi):#laivan koordinaatit, RGB vari lista
    for i in range(len(laiva_yksi)):
        cell_rect = pygame.Rect((((LEVEYS/11)*laiva_yksi[i][0])+(LEVEYS/11)), (((KORKEUS/11)*laiva_yksi[i][1])+(KORKEUS/11)), (LEVEYS/10.9), (KORKEUS/10.9))#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
        pygame.draw.rect(screen, (vari_yksi[0],vari_yksi[1], vari_yksi[2]), cell_rect)
        pygame.display.flip()

#asettaa laivan eri näppäimillä
#up,down,left,right, r kierto, y kyllä
def aseta_yksi_laiva(laivaTemp):#saa laiva listan ja jos muuttaa laiva parametria muuttuu myös alkuperäinen joka on funktiokutsussa
    vari_asetus=[33,55,66]
    
    if laivaTemp[0][0]==-1:#jos laivaa ei viela asetettu laitetaan vasenpaan yla reunaan A1 ruutuun
        for i in range(len(laivaTemp)):
            laivaTemp[i][0]=0
            laivaTemp[i][1]=i

    piirra_ruudukko()
    piirra_laivat()
    for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
            vari_asetus=[200,9,9]#jos mika tahansa paallekkain värjätään punaiseksi
    piirra_yksi_laiva(laivaTemp,vari_asetus)
    print("aseta laiva")

    asetus_Kesken=True
    while asetus_Kesken:#testataan mitä nappia painetaan laivojen sijoituksen aikana
        time.sleep(0.3)
        #print("while")
        for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sio.disconnect()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_DOWN:  # Host
                        print("KeyDown...")
                        if ((laivaTemp[0][1]<9) and (laivaTemp[-1][1]<9)):
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][1]+=1
                        #
                        vari_asetus=[33,55,66]
                        for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                vari_asetus=[200,9,9]
                        #
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp,vari_asetus)

                    elif event.key == pygame.K_UP:  # Join
                        print("Up")
                        if ((laivaTemp[0][1]>0) and (laivaTemp[-1][1]>0)):
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][1]-=1
                        #
                        vari_asetus=[33,55,66]
                        for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                vari_asetus=[200,9,9]
                        #
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp,vari_asetus)
                    elif event.key == pygame.K_LEFT:  # Join
                        print("Left")
                        if ((laivaTemp[0][0]>0) and (laivaTemp[-1][0]>0)):
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][0]-=1
                        #
                        vari_asetus=[33,55,66]
                        for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                vari_asetus=[200,9,9]
                        #
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp,vari_asetus)
                    elif event.key == pygame.K_RIGHT:  # Join
                        print("Right")
                        if ((laivaTemp[0][0]<9) and (laivaTemp[-1][0]<9)):
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][0]+=1
                        #
                        vari_asetus=[33,55,66]
                        for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                vari_asetus=[200,9,9]
                        #
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp,vari_asetus)
                    elif event.key == pygame.K_r:  # Join
                        print("rotate")
                        if (laivaTemp[0][0]==laivaTemp[-1][0]):#tosi jos pystytasossa
                            #
                            print("pystyssa")
                            lenLaiva=len(laivaTemp)
                            for i in range((len(laivaTemp))):
                                laivaTemp[i][1]=laivaTemp[0][1]
                                laivaTemp[i][0]=laivaTemp[0][0]+i
                            #nyt on vaakatasossa
                            if (laivaTemp[-1][0]>9):#tarkastaa menikö yli kentästä
                                overflow_temp=9-laivaTemp[-1][0]
                                for i in range(len(laivaTemp)):#
                                    laivaTemp[i][0]=laivaTemp[i][0]+overflow_temp
                            
                            vari_asetus=[33,55,66]
                            for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                                if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                    vari_asetus=[200,9,9]
                            #
                            piirra_ruudukko()
                            piirra_laivat()
                            piirra_yksi_laiva(laivaTemp,vari_asetus)
                            #
                            #
                            continue#pitää hypätä for loopin alkuun koska laiva käännetty ja seuraava if tulisi Tosi

                            #
                        if (laivaTemp[0][1]==laivaTemp[-1][1]):#tosi jos vaakatasossa
                            #
                            print("Vaakatasossa")
                            lenLaiva=len(laivaTemp)
                            for i in range((len(laivaTemp))):
                                laivaTemp[i][0]=laivaTemp[0][0]
                                laivaTemp[i][1]=laivaTemp[0][1]+i
                            #
                            if (laivaTemp[-1][1] > 9):#tarkastaa menikö yli
                                print("on yli")
                                overflow_temp=9-laivaTemp[-1][1]
                                print(overflow_temp)
                                for i in range(len(laivaTemp)):#
                                    laivaTemp[i][1]=laivaTemp[i][1]+overflow_temp

                            vari_asetus=[33,55,66]
                            for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                                if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                    vari_asetus=[200,9,9]
                            
                            piirra_ruudukko()
                            piirra_laivat()
                            piirra_yksi_laiva(laivaTemp,vari_asetus)
                            
                    elif event.key == pygame.K_y:  # 
                        print("Ok Tähän")
                        VoiAsettaa=True
                        for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                VoiAsettaa=False
                        if VoiAsettaa:
                            
                            asetus_Kesken=False#keskeyttää while loopin
                            break#keskeyttää for loopin
                        
    return laivaTemp#tämä palautetaan jos y painettu eikä ole päällekkäin
                            
def piirra_kaksi_ruudukkoa():
    # Määritellään vasemman (pelaajan) ruudun mitat
    left_board_width = LEVEYS / 2      # 400 pikseliä, jos LEVEYS on 800
    left_board_height = KORKEUS         # 600 pikseliä
    left_cell_width = left_board_width / 11   # Sama jako kuin alkuperäisessä piirrossa
    left_cell_height = left_board_height / 11

    # Tyhjennetään näyttö
    screen.fill((255, 255, 255))

    # Piirretään vasen ruudukko (pelaajan lauta)
    for i in range(11):
        # Pystylinjat
        pygame.draw.line(screen, (0, 0, 0),
                         (left_cell_width * i, 0),
                         (left_cell_width * i, left_board_height))
        # Vaakalinjat
        pygame.draw.line(screen, (0, 0, 0),
                         (0, left_cell_height * i),
                         (left_board_width, left_cell_height * i))
        if i > 0:
            # Numerot vasempaan reunaan
            number_text = fontti.render(str(i), True, (0, 0, 0))
            screen.blit(number_text, (left_cell_width * 0.1, left_cell_height * i + 5))
            # Kirjaimet yläreunaan
            letter_text = fontti.render(chr(i + 64), True, (0, 0, 0))
            screen.blit(letter_text, (left_cell_width * i + 5, left_cell_height * 0.1))

    # Piirretään oikea ruudukko (vihollisen lauta)
    right_board_offset = left_board_width  # Ruudun oikea puolisko alkaa tässä
    for i in range(11):
        # Pystylinjat, lisätään offset x-koordinaattiin
        pygame.draw.line(screen, (0, 0, 0),
                         (right_board_offset + left_cell_width * i, 0),
                         (right_board_offset + left_cell_width * i, left_board_height))
        # Vaakalinjat
        pygame.draw.line(screen, (0, 0, 0),
                         (right_board_offset, left_cell_height * i),
                         (right_board_offset + left_board_width, left_cell_height * i))
        if i > 0:
            # Numerot vihollisen laudan vasempaan reunaan
            number_text = fontti.render(str(i), True, (0, 0, 0))
            screen.blit(number_text, (right_board_offset + left_cell_width * 0.1, left_cell_height * i + 5))
            # Kirjaimet yläreunaan
            letter_text = fontti.render(chr(i + 64), True, (0, 0, 0))
            screen.blit(letter_text, (right_board_offset + left_cell_width * i + 5, left_cell_height * 0.1))

    #jos tämä flip ei päällä pitää seuraavassa esim laivojen piirrossa tehdä flip
    #pygame.display.flip()#tarvittaesssa poista kommenttista kun tämä flip päällä kenttä vilkkuu

def piirra_omatlaivat_kahteen_ruudukkoon():#piirtää laivat laivat 2d listasta pelikenttään jossa omat ja vihollisen kenttä
    global laivat#kerrotaan varmuudeksi että global lista muuttuja joka määritelty ihan alussa
    #ei aseta tai tee muuta kuin piirtää laivat
    ##print("piirretään omat laivat kahteen ruudukkoon")

    for x in range(len(laivat)):#piirtää laivat laivat 2d taulukosta jos 1
        #print(x)
        for y in range(len(laivat[x])):
            if(laivat[x][y]==1):
                cell_rect = pygame.Rect((((LEVEYS/22)*x)+(LEVEYS/22)), (((KORKEUS/11)*y)+(KORKEUS/11)), (LEVEYS/21.9), (KORKEUS/10.9))#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
                pygame.draw.rect(screen, (50, 50, 200), cell_rect)
                #pygame.display.flip()
    pygame.display.flip()






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

game_state = "start"  # Peli alkaa start-näkymästä

def main():
    """
    Pääfunktio, jossa on Pygamen pelisilmukka (while running).
    Ohjelma jakautuu eri pelitiloihin (start, setup_ships, playing).
    """
    global game_state
    clock = pygame.time.Clock()
    running = True
    start_screen = True
    
    while running:
        clock.tick(30)  # rajoitetaan päivitystaajuus ~30 fps

        # Kerätään kaikki tapahtumat listaan
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        # ==================== START-SCREEN TILA ======================
        if start_screen:
            # Käydään tapahtumat läpi start-näkymässä
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:
                        print("Hosting game...")
                        connect_to_server()
                        start_screen = False
                    elif event.key == pygame.K_j:
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False
                    elif event.key == pygame.K_a:
                        print("laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if host_rect.collidepoint(event.pos):
                        print("Hosting game...")
                        connect_to_server()
                        start_screen = False
                    elif join_rect.collidepoint(event.pos):
                        print("Joining game...")
                        connect_to_server()
                        start_screen = False
                    elif laivojen_asetus_rect.collidepoint(event.pos):
                        print("laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()

            # Piirretään start-näkymä joka kierroksella
            draw_start_screen()

        # ==================== SETUP_SHIPS TILA =======================
        elif game_state == "setup_ships":
            # Siirrytään laivojen asetteluun
            print("Siirrytään laivojen asetteluun...")
            screen.fill((255, 255, 255))
            aseta_laivat()
            game_state = "playing"  # Kun laivat on asetettu, siirrytään pelaamiseen

        # ==================== PLAYING TILA ==========================
        elif game_state == "playing":
            # Käsitellään tapahtumat playing-tilassa
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos

                    # Lasketaan oikean puolen (”vihollisen laudan”) rajat
                    left_board_width = LEVEYS / 2
                    left_cell_width = (LEVEYS / 2) / 11
                    left_cell_height = KORKEUS / 11

                    # Jos klikattiin oikeanpuoleista laudan aluetta
                    if mouse_x > left_board_width:
                        oikea_offset = mouse_x - left_board_width
                        cell_x = int(oikea_offset // left_cell_width)
                        cell_y = int(mouse_y // left_cell_height)

                        if 0 <= cell_x < 10 and 0 <= cell_y < 10:
                            print(f"Klikkasit vastustajan ruudukon ruutua: ({cell_x}, {cell_y})")
                            # Lähetetään pommitus palvelimelle
                            sio.emit('shoot_bomb', {'x': cell_x, 'y': cell_y})

            # Piirretään pelinäkymä joka kierroksella
            piirra_kaksi_ruudukkoa()
            piirra_omatlaivat_kahteen_ruudukkoon()
            clock.tick(30)

    # Kun running = False, poistutaan silmukasta:
    sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
    
#socketio kuuntelija
@sio.on("bomb_update")
def on_bomb_update(data):
    """
    Palvelimelta tulee viesti pommituksen koordinaateista,
    ja tämä funktio päivittää bomb_data -taulukon sekä piirtää pommituksen.
    """
    x = data["x"]
    y = data["y"]
    update_bomb_data(x, y)  # Merkitään pommitus local-bomb_dataan
    piirra_pommitukset()    # Piirretään punainen piste