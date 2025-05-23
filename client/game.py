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


# Alueet ja ruudukon piirtämiseen liittyvät muuttujat
host_rect = pygame.Rect(LEVEYS // 2 - 160, 300, 150, 50)#mitta vasemmasta reunasta,ylhäältä,leveys,korkeus
join_rect = pygame.Rect(LEVEYS // 2 + 5, 300, 150, 50)
laivojen_asetus_rect = pygame.Rect(((LEVEYS/2)-150), 400, 300, 50)

# 2D-listat laivoille ja pommituksille
#2d lista 10*10 laivoille  pelikenttä 0=ei laivaa 1=on laiva
laivat = [[0]*10 for _ in range(10)]
own_bomb_data = [[0]*10 for _ in range(10)]  # Omat laivat + pommitukset (Pommit jotka vastustaja on ampunut 2 = osuma, 1 = ohi, 0 = ei aiempaa pommitusta)
opponent_bomb_data = [[0]*10 for _ in range(10)]  # Vastustajan ruudukko(Pommit jotka ammuttu vastustajan laivoihin 2 = osuma, 1 = ohi,0 = ei aiempaa pommitusta)

#Pisteenlaskennan muuttujat
osumat_omiin_laivoihin=0
osumat_vastustajan_laivoihin=0

#Laivojen ruutumäärä, käytetään loppuruudussa sekä asetetan laske pisteet funktiossa
TOTAL_SHIP_PARTS = 18

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

def tarkista_havio():

    #Tarkistaa, ovatko kaikki oman puolen laivat uponneet.
    #Palauttaa True, jos pelaaja on hävinnyt

    omat_laivat = 0
    osumat_omiin = 0
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                omat_laivat += 1
                if own_bomb_data[x][y] == 2:  # 2 tarkoittaa osumaa omassa ruudukossa
                    osumat_omiin += 1
    return (omat_laivat == osumat_omiin and omat_laivat > 0)


def tarkista_voitto():
    
    #Tarkistaa, onko pelaaja saanut riittävästi osumia vastustajan laivoihin (18).
    #Palauttaa True, jos pelaaja on voittanut.
    
    osumat_vastustajaan = 0
    for x in range(len(opponent_bomb_data)):
        for y in range(len(opponent_bomb_data[x])):
            if opponent_bomb_data[x][y] == 2:  # 2 = osuma vastustajan laivaan
                osumat_vastustajaan += 1

    # Jos osumien määrä on yhtä suuri kuin vastustajan laivojen yhteispituus
    return (osumat_vastustajaan >= TOTAL_SHIP_PARTS)

def piirra_havioruutu():
    
    #Piirtää häviöruudun, jossa lukee "Hävisit pelin! Paina ESC poistuaksesi".
    
    screen.fill((0, 0, 0))
    teksti = fontti.render("Hävisit pelin! Paina ESC poistuaksesi", True, (255, 0, 0))
    screen.blit(teksti, (LEVEYS // 2 - teksti.get_width() // 2, KORKEUS // 2))
    pygame.display.flip()

def piirra_voittoruutu():
    
    #Piirtää voittoruudun, jossa lukee "Voitit pelin! Paina ESC poistuaksesi".
    
    screen.fill((255, 255, 255))
    teksti = fontti.render("Voitit pelin! Paina ESC poistuaksesi", True, (0, 128, 0))
    screen.blit(teksti, (LEVEYS // 2 - teksti.get_width() // 2, KORKEUS // 2))
    pygame.display.flip()

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

    pygame.display.flip()
    time.sleep(2)

#lähinnä aseta yksi laiva funktiota varten
#piirtää laivan mutta ei lisää mitään laivat 2dListaan
def piirra_yksi_laiva(laiva_yksi, vari_yksi):#laivan koordinaatit, RGB vari lista
    for i in range(len(laiva_yksi)):
        cell_rect = pygame.Rect(((LEVEYS/11)*laiva_yksi[i][0])+(LEVEYS/11), ((KORKEUS/11)*laiva_yksi[i][1])+(KORKEUS/11), LEVEYS/10.9, KORKEUS/10.9)
        pygame.draw.rect(screen, (vari_yksi[0], vari_yksi[1], vari_yksi[2]), cell_rect)


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

    laske_pisteet()#asettaa piste muuttujat
    pisteet_teksti = fontti.render(f"pisteesi {osumat_vastustajan_laivoihin}/{TOTAL_SHIP_PARTS}", 
                                True, (255, 0, 0))
    screen.blit(pisteet_teksti, (LEVEYS//2 - pisteet_teksti.get_width()//2, KORKEUS-30))
    


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

    tempSumOmat=0
    tempSumSamaKuinOpponent=0
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                tempSumOmat+=1#tempsumomat tulee niin isoksi kuin laivoja on
                            #pitäisi siis aina olla vakio riippuen laivojen määrästä 
                            # mutta lasketaan jos halutaankin eri määrä laivoja
            if ((laivat[x][y]==1) and (own_bomb_data[x][y]==2)):
                            #own_bomb_data 0=ei ammuttu 1=ohi  2=osuma
                            #testaa onko siis vastustaja ampunut samaan rutuun
                            #kuin missä oma laiva on
                tempSumSamaKuinOpponent+=1
    
    if (tempSumOmat==tempSumSamaKuinOpponent):#jos samat niin silloin kaikkiin laivoihin osunut
        print("Hävisit Kaikki lavat ovat uponneet")#
        #
        aakkonen_text = fontti.render("HÄVISIT", True, (0,0,0))
        screen.blit(aakkonen_text, ((LEVEYS/2), (KORKEUS/2)))#hävisit teksti
        pygame.time.Clock().tick(300)
        #tähän käsittely häviämiselle
        #
        #

def laske_pisteet():
    global osumat_omiin_laivoihin
    global osumat_vastustajan_laivoihin
    global TOTAL_SHIP_PARTS
    #
    osumat_omiin_laivoihin=0
    for x in range(len(own_bomb_data)):
        for y in range(len(own_bomb_data[x])):
            if (own_bomb_data[x][y]==2):#jos tosi osuma omaan laivaan
                osumat_omiin_laivoihin+=1
    
    osumat_vastustajan_laivoihin=0
    for x in range(len(opponent_bomb_data)):
        for y in range(len(opponent_bomb_data[x])):
            if (opponent_bomb_data[x][y]==2):#jos tosi osuma vastustajan laivaan
                osumat_vastustajan_laivoihin+=1
    #
    TOTAL_SHIP_PARTS=0
    for x in range(len(laivat)):
        for y in range(len(laivat[x])):
            if laivat[x][y] == 1:
                TOTAL_SHIP_PARTS+=1#TOTAL_SHIP_PARTS tulee niin isoksi kuin laivoja on esim lentotukialus on 5 pistettä
    
    print(f"Kaikki pisteet {TOTAL_SHIP_PARTS}")
    print(f"Vastustajan pisteet {osumat_omiin_laivoihin}")
    print(f"Omat pisteet {osumat_vastustajan_laivoihin}")


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

def run_game():
    global game_state
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
            elif event.type == GAME_STATE_UPDATE:
                game_state = event.new_state
                print("Pelitila päivittyi:", game_state)
            elif event.type == pygame.USEREVENT:
                if hasattr(event, 'custom_type'):
                    if event.custom_type == 'turn_update':
                        print("Vuoro päivittyi - päivitetään näyttö")
                        update_game_display()
                    elif event.custom_type == 'bomb_update':
                        print("Pommitustieto päivittyi - päivitetään näyttö")
                        update_game_display()
        if start_screen:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:
                        print("Hosting game...")
                        network.connect_to_server()
                        start_screen = False
                    elif event.key == pygame.K_j:
                        print("Joining game...")
                        network.connect_to_server()
                        start_screen = False
                    elif event.key == pygame.K_a:
                        print("laivojen asettaminen...")
                        aseta_laivat()
                        draw_start_screen()
                elif event.type == pygame.MOUSEBUTTONDOWN:
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
            draw_start_screen()
        elif game_state == "setup_ships":
            print("Siirrytään laivojen asetteluun...")
            screen.fill((255, 255, 255))
            aseta_laivat()
            # Kerätään laivojen koordinaatit ja lähetetään palvelimelle
            all_ships = []
            for ship in [lentotukialus, taistelulaiva, risteilija1, risteilija2, havittaja, sukellusvene]:
                for coord in ship:
                    if coord[0] != -1:
                        all_ships.append(coord)
            network.sio.emit('set_ships', {'ships': all_ships})
            pygame.event.post(pygame.event.Event(GAME_STATE_UPDATE, {"new_state": "playing"}))

        elif game_state == "playing":
        # Piirrä ruudukot ja tilanne
            # piirra_kaksi_ruudukkoa()
            # piirra_omatlaivat_kahteen_ruudukkoon()
            # piirra_pommitukset()
            testaa_onko_kaikki_uponnut()
            
            # Näytä vuorotiedote ruudulla
            vuoro_teksti = fontti.render("SINUN VUOROSI" if network.my_turn else "VASTUSTAJAN VUORO", True, (255, 0, 0))
            screen.blit(vuoro_teksti, (LEVEYS//2 - vuoro_teksti.get_width()//2, 20))
            pygame.display.flip()
            
            for event in events:
                update_game_display()
                if event.type == pygame.MOUSEBUTTONDOWN and network.my_turn:
                    mouse_x, mouse_y = event.pos
                    left_board_width = LEVEYS / 2
                    
                    if mouse_x > left_board_width:
                        oikea_offset = mouse_x - left_board_width
                        cell_width = (LEVEYS / 2) / 11
                        cell_height = KORKEUS / 11
                        
                        cell_x = int(oikea_offset // cell_width)-1#hätä korjaus -1
                        cell_y = int(mouse_y // cell_height)-1#hätä korjaus -1
                        
                        if 0 <= cell_x < 10 and 0 <= cell_y < 10:
                            if opponent_bomb_data[cell_x][cell_y] == 0:
                                print(f"Ammutaan ruutuun: ({cell_x}, {cell_y})")
                                 # Lähetetään palvelimelle 'shoot_bomb'-tapahtuma, jossa kerrotaan ammutun ruudun koordinaatit
                                network.sio.emit('shoot_bomb', {'x': cell_x, 'y': cell_y})
                            else:
                                print("Tähän ruutuun on jo ammuttu!")
                            update_game_display()
                            laske_pisteet()

            # Tarkistetaan pelaajan häviö/voitto
            if tarkista_havio():
                game_state = "lose"
            elif tarkista_voitto():
                game_state = "win"

        elif game_state == "lose":
            # Näytetään häviöruutu
            piirra_havioruutu()
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

        elif game_state == "win":
            # Näytetään voittoruutu
            piirra_voittoruutu()
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

    network.sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game()