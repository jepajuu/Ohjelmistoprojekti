import pygame
import sys
import time
import copy#tämä tarvitaan että voi tehdä sisäkkäisille listoille copyn
import network
#pip install "python-socketio"

pygame.init()
pygame.font.init()
GAME_STATE_UPDATE = pygame.USEREVENT + 1

# Määritellään globaalit muuttujat ja asetukset
LEVEYS, KORKEUS = 800, 600
fontti = pygame.font.SysFont(None, 50)
screen = pygame.display.set_mode((LEVEYS, KORKEUS), pygame.RESIZABLE)
pygame.display.set_caption("Laivanupotus")

game_over = False
winner_text = ""

ships_set = False


# Alueet ja ruudukon piirtämiseen liittyvät muuttujat
host_rect = pygame.Rect(LEVEYS // 2 - 160, 300, 150, 50)#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
join_rect = pygame.Rect(LEVEYS // 2 + 5, 300, 150, 50)
laivojen_asetus_rect = pygame.Rect(((LEVEYS/2)-150), 400, 300, 50)

# 2D-listat laivoille ja pommituksille
#2d lista 10*10 laivoille  pelikenttä 0=ei laivaa 1=on laiva
laivat = [[0]*10 for _ in range(10)]
own_bomb_data = [[0]*10 for _ in range(10)]  # Omat laivat + pommitukset (Pommit jotka vastustaja on ampunut)
opponent_bomb_data = [[0]*10 for _ in range(10)]  # Vastustajan ruudukko(Pommit jotka ammuttu vastustajan laivoihin)

# Esimerkkilaivat
#arvot voi olla 0-9   [A-J, 1-10]
lentotukialus = [[-1, -1], [2,3], [2,4], [2,5], [2,6]]
lentotukialusCopy = copy.deepcopy(lentotukialus)
taistelulaiva = [[-1, -1], [9,1], [9,2], [9,3]]
taistelulaivaCopy = copy.deepcopy(taistelulaiva)
risteilija1 = [[-1, -1], [1,2], [1,3]]
risteilija1Copy = copy.deepcopy(risteilija1)
risteilija2 = [[-1, -1], [1,6], [2,6]]
risteilija2Copy = copy.deepcopy(risteilija2)
havittaja = [[-1, -1], [-1, -1]]
havittajaCopy = copy.deepcopy(havittaja)
sukellusvene = [[-1, -1]]
sukellusveneCopy = copy.deepcopy(sukellusvene)

def piirra_ruudukko():
    screen.fill((255,255,255))
    for i in range(11):
        pygame.draw.line(screen, (0,0,0), [(LEVEYS/11)*i, 0], [(LEVEYS/11)*i, KORKEUS])
        pygame.draw.line(screen, (0,0,0), [0, (KORKEUS/11)*i], [LEVEYS, (KORKEUS/11)*i])
        if i > 0:
            number_text = fontti.render(str(i), True, (0,0,0))
            screen.blit(number_text, ((LEVEYS/11)*0.1, (KORKEUS/11)*i+5))
            aakkonen_text = fontti.render(chr(i+64), True, (0,0,0))
            screen.blit(aakkonen_text, (((LEVEYS/11)*i)+5, (KORKEUS/11)*0.1))


def piirra_laivat():#myös asettaa laivat 2d listaan
    global laivat
    for i in range(len(laivat)):
        for r in range(len(laivat[i])):
            laivat[i][r] = 0
    if lentotukialus[0][0] != -1:
        for i in range(len(lentotukialus)):
            #ja asettaa laivat 2d taulukon solut ykköseksi joissa lentotukialus on
            laivat[lentotukialus[i][0]][lentotukialus[i][1]] = 1
    if taistelulaiva[0][0] != -1:
        for i in range(len(taistelulaiva)):
            laivat[taistelulaiva[i][0]][taistelulaiva[i][1]] = 1
    if risteilija1[0][0] != -1:
        for i in range(len(risteilija1)):
            laivat[risteilija1[i][0]][risteilija1[i][1]] = 1
    if risteilija2[0][0] != -1:
        for i in range(len(risteilija2)):
            laivat[risteilija2[i][0]][risteilija2[i][1]] = 1
    if havittaja[0][0] != -1:
        for i in range(len(havittaja)):
            laivat[havittaja[i][0]][havittaja[i][1]] = 1
    if sukellusvene[0][0] != -1:
        for i in range(len(sukellusvene)):
            laivat[sukellusvene[i][0]][sukellusvene[i][1]] = 1
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                cell_rect = pygame.Rect(((LEVEYS/11)*x)+(LEVEYS/11), ((KORKEUS/11)*y)+(KORKEUS/11), LEVEYS/10.9, KORKEUS/10.9)
                pygame.draw.rect(screen, (50,50,200), cell_rect)


# Päivittää oman ruudukon (own_bomb_data) tiedon siitä, osuiko vastustajan laukaus omiin laivoihin
def update_bomb_data(x, y):
    # Tarkistetaan, onko kyseiseen ruutuun jo osuttu tai ammuttu (0 = ei aiempaa pommitusta)
    if own_bomb_data[x][y] == 0:
        # Jos kohdassa on oma laiva (1), kyseessä on osuma
        if laivat[x][y] == 1:
            print("Osuma!")
            own_bomb_data[x][y] = 2  # 2 tarkoittaa osumaa omassa ruudukossa
        else:
            print("Ohitus!")
            own_bomb_data[x][y] = 1  # 1 tarkoittaa ohilaukausta omassa ruudukossa


def piirra_pommitukset():
    left_cell_width = (LEVEYS / 2) / 11
    right_cell_width = (LEVEYS / 2) / 11
    cell_height = KORKEUS / 11
    
    # Oma ruudukko (vasen) - vastustajan laukaukset
    for x in range(10):
        for y in range(10):
            if own_bomb_data[x][y] != 0:
                left_cell_x = left_cell_width * (x + 1)
                left_cell_y = cell_height * (y + 1)
                
                if own_bomb_data[x][y] == 2:  # Osuma
                    # Punainen täysi ympyrä
                    pygame.draw.circle(screen, (255, 0, 0), 
                                     (int(left_cell_x + left_cell_width/2), 
                                      int(left_cell_y + cell_height/2)), 
                                     int(left_cell_width/3))
                else:  # Ohilaukaus
                    # Musta rengas
                    pygame.draw.circle(screen, (0, 0, 0), 
                                     (int(left_cell_x + left_cell_width/2), 
                                      int(left_cell_y + cell_height/2)), 
                                     int(left_cell_width/3), 2)

    # Vastustajan ruudukko (oikea) - omat laukaukset
    for x in range(10):
        for y in range(10):
            if opponent_bomb_data[x][y] != 0:
                right_cell_x = (LEVEYS / 2) + right_cell_width * (x + 1)
                right_cell_y = cell_height * (y + 1)
                
                if opponent_bomb_data[x][y] == 2:  # Osuma
                    # Punainen risti (X)
                    cross_size = right_cell_width / 3
                    center_x = right_cell_x + right_cell_width / 2
                    center_y = right_cell_y + cell_height / 2
                    pygame.draw.line(screen, (255, 0, 0),
                                   (int(center_x - cross_size), 
                                    int(center_y - cross_size)),
                                   (int(center_x + cross_size), 
                                    int(center_y + cross_size)), 3)
                    pygame.draw.line(screen, (255, 0, 0),
                                   (int(center_x + cross_size), 
                                    int(center_y - cross_size)),
                                   (int(center_x - cross_size), 
                                    int(center_y + cross_size)), 3)
                else:  # Ohilaukaus
                    # Sininen ympyrä
                    pygame.draw.circle(screen, (0, 0, 255), 
                                     (int(right_cell_x + right_cell_width/2), 
                                      int(right_cell_y + cell_height/2)), 
                                     int(right_cell_width/4))

def aseta_laivat():
    piirra_ruudukko()
    piirra_laivat()
    global taistelulaiva, taistelulaivaCopy
    taistelulaivaCopy = copy.deepcopy(taistelulaiva)
    taistelulaiva[0][0] = -1
    taistelulaiva = aseta_yksi_laiva(taistelulaivaCopy)
    piirra_ruudukko()
    piirra_laivat()
    global lentotukialus, lentotukialusCopy
    lentotukialusCopy = copy.deepcopy(lentotukialus)
    lentotukialus[0][0] = -1
    lentotukialus = aseta_yksi_laiva(lentotukialusCopy)
    piirra_ruudukko()
    piirra_laivat()
    global risteilija1, risteilija1Copy
    risteilija1Copy = copy.deepcopy(risteilija1)
    risteilija1[0][0] = -1
    risteilija1 = aseta_yksi_laiva(risteilija1Copy)
    piirra_ruudukko()
    piirra_laivat()
    global risteilija2, risteilija2Copy
    risteilija2Copy = copy.deepcopy(risteilija2)
    risteilija2[0][0] = -1
    risteilija2 = aseta_yksi_laiva(risteilija2Copy)
    piirra_ruudukko()
    piirra_laivat()
    global havittaja, havittajaCopy
    havittajaCopy = copy.deepcopy(havittaja)
    havittaja[0][0] = -1
    havittaja = aseta_yksi_laiva(havittajaCopy)
    piirra_ruudukko()
    piirra_laivat()
    global sukellusvene, sukellusveneCopy
    sukellusveneCopy = copy.deepcopy(sukellusvene)
    sukellusvene[0][0] = -1
    sukellusvene = aseta_yksi_laiva(sukellusveneCopy)
    piirra_ruudukko()
    piirra_laivat()

    # Kerätään laivojen koordinaatit ja lähetetään palvelimelle
    all_ships = []
    for ship in [lentotukialus, taistelulaiva, risteilija1, risteilija2, havittaja, sukellusvene]:
        for coord in ship:
            if coord[0] != -1:
                all_ships.append(coord)
    
    # Lähetä laivat palvelimelle ja ilmoita valmiudesta
    network.sio.emit('set_ships', {'ships': all_ships})
    network.sio.emit('ships_ready', {})
    
    pygame.display.flip()
    return True  # Palauta True kun laivat on asetettu

#lähinnä aseta yksi laiva funktiota varten
#piirtää laivan mutta ei lisää mitään laivat 2dListaan
def piirra_yksi_laiva(laiva_yksi, vari_yksi):#laivan koordinaatit, RGB vari lista
    for i in range(len(laiva_yksi)):
        cell_rect = pygame.Rect(((LEVEYS/11)*laiva_yksi[i][0])+(LEVEYS/11), ((KORKEUS/11)*laiva_yksi[i][1])+(KORKEUS/11), LEVEYS/10.9, KORKEUS/10.9)
        pygame.draw.rect(screen, (vari_yksi[0], vari_yksi[1], vari_yksi[2]), cell_rect)


# game.py (lisäys)
def update_game_display():
    """Päivittää ruudun sisällön"""
    screen.fill((255, 255, 255))
    piirra_kaksi_ruudukkoa()
    piirra_omatlaivat_kahteen_ruudukkoon()
    piirra_pommitukset()
    
    # Näytä vuorotilanne
    vuoro_teksti = fontti.render("SINUN VUOROSI" if network.my_turn else "VASTUSTAJAN VUORO", 
                                True, (255, 0, 0) if network.my_turn else (0, 0, 255))
    screen.blit(vuoro_teksti, (LEVEYS//2 - vuoro_teksti.get_width()//2, 20))


    #asettaa laivan eri näppäimillä
#up,down,left,right, r kierto, y kyllä
def aseta_yksi_laiva(laivaTemp):
    #saa laiva listan ja jos muuttaa laiva parametria 
    # muuttuu myös alkuperäinen joka on funktiokutsussa
    vari_asetus = [33,55,66]
    if laivaTemp[0][0] == -1:#jos laivaa ei viela asetettu laitetaan vasenpaan yla reunaan A1 ruutuun
        for i in range(len(laivaTemp)):
            laivaTemp[i][0] = 0
            laivaTemp[i][1] = i
    piirra_ruudukko()
    piirra_laivat()
    for i in range(len(laivaTemp)):#testaa onko päällekkäisiä
        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
            vari_asetus = [200,9,9]#jos mika tahansa paallekkain värjätään punaiseksi
    piirra_yksi_laiva(laivaTemp, vari_asetus)
    pygame.display.flip() # piirtää alkutilanteen

    print("aseta laiva")
    asetus_Kesken = True
    while asetus_Kesken:#testataan mitä nappia painetaan laivojen sijoituksen aikana
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                from network import sio
                sio.disconnect()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    print("KeyDown...")
                    if laivaTemp[0][1] < 9 and laivaTemp[-1][1] < 9:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][1] += 1
                    vari_asetus = [33,55,66]
                    for i in range(len(laivaTemp)):
                        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                            vari_asetus = [200,9,9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                    pygame.display.flip()
                elif event.key == pygame.K_UP:
                    print("Up")
                    if laivaTemp[0][1] > 0 and laivaTemp[-1][1] > 0:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][1] -= 1
                    vari_asetus = [33,55,66]
                    for i in range(len(laivaTemp)):
                        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                            vari_asetus = [200,9,9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                    pygame.display.flip()
                elif event.key == pygame.K_LEFT:
                    print("Left")
                    if laivaTemp[0][0] > 0 and laivaTemp[-1][0] > 0:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][0] -= 1
                    vari_asetus = [33,55,66]
                    for i in range(len(laivaTemp)):
                        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                            vari_asetus = [200,9,9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                    pygame.display.flip()
                elif event.key == pygame.K_RIGHT:
                    print("Right")
                    if laivaTemp[0][0] < 9 and laivaTemp[-1][0] < 9:
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][0] += 1
                    vari_asetus = [33,55,66]
                    for i in range(len(laivaTemp)):
                        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                            vari_asetus = [200,9,9]
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                    pygame.display.flip()
                elif event.key == pygame.K_r:
                    print("rotate")
                    if laivaTemp[0][0] == laivaTemp[-1][0]:
                        print("pystyssa")
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][1] = laivaTemp[0][1]
                            laivaTemp[i][0] = laivaTemp[0][0] + i
                        if laivaTemp[-1][0] > 9:
                            overflow_temp = 9 - laivaTemp[-1][0]
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][0] += overflow_temp
                        vari_asetus = [33,55,66]
                        for i in range(len(laivaTemp)):
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                vari_asetus = [200,9,9]
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp, vari_asetus)
                        pygame.display.flip()
                        continue#pitää hypätä for loopin alkuun koska laiva käännetty ja seuraava if tulisi Tosi
                    if laivaTemp[0][1] == laivaTemp[-1][1]:
                        print("Vaakatasossa")
                        for i in range(len(laivaTemp)):
                            laivaTemp[i][0] = laivaTemp[0][0]
                            laivaTemp[i][1] = laivaTemp[0][1] + i
                        if laivaTemp[-1][1] > 9:
                            overflow_temp = 9 - laivaTemp[-1][1]
                            for i in range(len(laivaTemp)):
                                laivaTemp[i][1] += overflow_temp
                        vari_asetus = [33,55,66]
                        for i in range(len(laivaTemp)):
                            if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                                vari_asetus = [200,9,9]
                        piirra_ruudukko()
                        piirra_laivat()
                        piirra_yksi_laiva(laivaTemp, vari_asetus)
                        pygame.display.flip()
                elif event.key == pygame.K_y:
                    print("Ok Tähän")
                    VoiAsettaa = True
                    for i in range(len(laivaTemp)):
                        if laivat[laivaTemp[i][0]][laivaTemp[i][1]]:
                            VoiAsettaa = False
                    if VoiAsettaa:
                        asetus_Kesken = False
                        break
                    piirra_ruudukko()
                    piirra_laivat()
                    piirra_yksi_laiva(laivaTemp, vari_asetus)
                    pygame.display.flip()

    return laivaTemp

def piirra_kaksi_ruudukkoa():
    left_board_width = LEVEYS / 2
    left_board_height = KORKEUS
    left_cell_width = left_board_width / 11
    left_cell_height = left_board_height / 11
    screen.fill((255,255,255))
    for i in range(11):
        pygame.draw.line(screen, (0,0,0), (left_cell_width * i, 0), (left_cell_width * i, left_board_height))
        pygame.draw.line(screen, (0,0,0), (0, left_cell_height * i), (left_board_width, left_cell_height * i))
        if i > 0:
            number_text = fontti.render(str(i), True, (0,0,0))
            screen.blit(number_text, (left_cell_width * 0.1, left_cell_height * i + 5))
            letter_text = fontti.render(chr(i+64), True, (0,0,0))
            screen.blit(letter_text, (left_cell_width * i + 5, left_cell_height * 0.1))
    right_board_offset = left_board_width
    for i in range(11):
        pygame.draw.line(screen, (0,0,0), (right_board_offset + left_cell_width * i, 0), (right_board_offset + left_cell_width * i, left_board_height))
        pygame.draw.line(screen, (0,0,0), (right_board_offset, left_cell_height * i), (right_board_offset + left_board_width, left_cell_height * i))
        if i > 0:
            number_text = fontti.render(str(i), True, (0,0,0))
            screen.blit(number_text, (right_board_offset + left_cell_width * 0.1, left_cell_height * i + 5))
            letter_text = fontti.render(chr(i+64), True, (0,0,0))
            screen.blit(letter_text, (right_board_offset + left_cell_width * i + 5, left_cell_height * 0.1))

def piirra_omatlaivat_kahteen_ruudukkoon():
    global laivat
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                cell_rect = pygame.Rect(((LEVEYS/22)*x)+(LEVEYS/22), ((KORKEUS/11)*y)+(KORKEUS/11), LEVEYS/21.9, KORKEUS/10.9)
                pygame.draw.rect(screen, (50,50,200), cell_rect)


def testaa_onko_kaikki_uponnut():
    global game_over, winner_text
    
    tempSumOmat = 0
    tempSumSamaKuinOpponent = 0
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                tempSumOmat += 1
            if ((laivat[x][y] == 1) and (own_bomb_data[x][y] == 2)):
                tempSumSamaKuinOpponent += 1
    
    if tempSumOmat == tempSumSamaKuinOpponent:
        game_over = True
        winner_text = "HÄVISIT"
        print("Hävisit - Kaikki laivat ovat uponneet")
        return True
    
    # Tarkista onko vastustajan laivat upotettu
    opponent_hits = 0
    for x in range(10):
        for y in range(10):
            if opponent_bomb_data[x][y] == 2:
                opponent_hits += 1
    
    # Jos vastustaja on uponnut kaikki laivasi (oletetaan 17 ruutua laivoja)
    if opponent_hits >= 17:  # Voit säätää tätä laivojen kokonaismäärän mukaan
        game_over = True
        winner_text = "VOITIT"
        print("Voitit - Kaikki vastustajan laivat uponneet")
        return True
    
    return False


def draw_start_screen():
    screen.fill((0,0,0))
    otsikko = fontti.render("Laivanupotus peli :D", True, (255,255,255))
    pygame.draw.rect(screen, (50,50,200), host_rect)
    pygame.draw.rect(screen, (50,200,50), join_rect)
    pygame.draw.rect(screen, (50,200,50), laivojen_asetus_rect)
    host_text = fontti.render("HOST", True, (255,255,255))
    join_text = fontti.render("JOIN", True, (255,255,255))
    laivojen_asetus_text = fontti.render("ASETA LAIVAT", True, (255,255,255))
    screen.blit(otsikko, (LEVEYS//2 - otsikko.get_width()//2, 150))
    screen.blit(host_text, (host_rect.x+35, host_rect.y+10))
    screen.blit(join_text, (join_rect.x+35, join_rect.y+10))
    screen.blit(laivojen_asetus_text, (laivojen_asetus_rect.x+35, laivojen_asetus_rect.y+10))
    pygame.display.flip()

game_state = "start"

def reset_game():
    global game_over, winner_text, laivat, own_bomb_data, opponent_bomb_data
    global lentotukialus, taistelulaiva, risteilija1, risteilija2, havittaja, sukellusvene
    global ships_set, game_state
    
    # Nollaa pelitilanne
    game_over = False
    winner_text = ""
    ships_set = False
    game_state = "setup_ships"
    
    # Nollaa ruudukot
    laivat = [[0]*10 for _ in range(10)]
    own_bomb_data = [[0]*10 for _ in range(10)]
    opponent_bomb_data = [[0]*10 for _ in range(10)]
    
    # Palauta laivat alkuperäiseen asentoon
    lentotukialus = [[-1, -1], [2,3], [2,4], [2,5], [2,6]]
    taistelulaiva = [[-1, -1], [9,1], [9,2], [9,3]]
    risteilija1 = [[-1, -1], [1,2], [1,3]]
    risteilija2 = [[-1, -1], [1,6], [2,6]]
    havittaja = [[-1, -1], [-1, -1]]
    sukellusvene = [[-1, -1]]
    
    # Pyydä palvelinta resetöimään peli
    network.sio.emit('reset_game')

# game.py (muutokset)
def run_game():
    global game_state, game_over, ships_set, start_screen
    
    clock = pygame.time.Clock()
    running = True
    start_screen = True
    
    if not network.sio.connected:
        network.connect_to_server()

    while running:
        clock.tick(30)
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game_over and event.key == pygame.K_r:  # Paina R aloittaaksesi uuden pelin
                    reset_game()
                elif event.key == pygame.K_h and start_screen:
                    print("Hosting game...")
                    network.connect_to_server()
                    start_screen = False
                elif event.key == pygame.K_j and start_screen:
                    print("Joining game...")
                    network.connect_to_server()
                    start_screen = False
                elif event.key == pygame.K_a and start_screen:
                    print("laivojen asettaminen...")
                    aseta_laivat()
                    draw_start_screen()
            elif event.type == GAME_STATE_UPDATE:
                game_state = event.new_state
                if game_state == "setup_ships":
                    ships_set = False
                elif game_state == "playing":
                    update_game_display()  # Päivitä näyttö välittömästi pelitilaan
            elif event.type == pygame.USEREVENT:
                if hasattr(event, 'custom_type'):
                    if event.custom_type == 'turn_update':
                        update_game_display()
                    elif event.custom_type == 'bomb_update':
                        update_game_display()
                        testaa_onko_kaikki_uponnut()  # Tarkista pelin loppuminen jokaisen päivityksen jälkeen
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if start_screen:
                    if host_rect.collidepoint(event.pos):
                        print("Hosting game...")
                        network.connect_to_server()
                        start_screen = False
                    elif join_rect.collidepoint(event.pos):
                        print("Joining game...")
                        network.connect_to_server()
                        start_screen = False
                    elif laivojen_asetus_rect.collidepoint(event.pos):
                        print("laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()
                elif game_state == "playing" and network.my_turn:
                    mouse_x, mouse_y = event.pos
                    left_board_width = LEVEYS / 2
                    
                    if mouse_x > left_board_width:
                        oikea_offset = mouse_x - left_board_width
                        cell_width = (LEVEYS / 2) / 11
                        cell_height = KORKEUS / 11
                        
                        cell_x = int(oikea_offset // cell_width)-1
                        cell_y = int(mouse_y // cell_height)-1
                        
                        if 0 <= cell_x < 10 and 0 <= cell_y < 10:
                            if opponent_bomb_data[cell_x][cell_y] == 0:
                                print(f"Ammutaan ruutuun: ({cell_x}, {cell_y})")
                                network.sio.emit('shoot_bomb', {'x': cell_x, 'y': cell_y})
                            else:
                                print("Tähän ruutuun on jo ammuttu!")
                            update_game_display()
        
        if game_over:
            # Näytä lopputeksti ja ohje uuden pelin aloittamiseen
            screen.fill((255, 255, 255))
            result_text = fontti.render(winner_text, True, (255, 0, 0) if winner_text == "VOITIT" else (0, 0, 255))
            restart_text = fontti.render("Paina R aloittaaksesi uuden pelin", True, (0, 0, 0))
            screen.blit(result_text, (LEVEYS//2 - result_text.get_width()//2, KORKEUS//2 - 50))
            screen.blit(restart_text, (LEVEYS//2 - restart_text.get_width()//2, KORKEUS//2 + 50))
            pygame.display.flip()
            continue
            
        if start_screen:
            draw_start_screen()
        elif game_state == "setup_ships":
            if not ships_set:
                print("Asetetaan laivat...")
                ships_set = aseta_laivat()  # Odota kunnes laivat on asetettu
            else:
                # Odota että peli siirtyy playing-tilaan palvelimelta
                pass
        elif game_state == "playing":
            update_game_display()
            pygame.display.flip()
    network.sio.disconnect()
    pygame.quit()
    sys.exit()
if __name__ == "__main__":
    run_game()