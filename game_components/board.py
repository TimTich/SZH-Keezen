from space import Space
from player import Player
from deck import Deck

class Board:
    spaces = []
    players = []

    def __init__(self):
        self.fillSpaces()
        self.detectPlayers
    
    def fillSpaces(self):
        for number in range(64):
            if number % 16 == 0:
                self.spaces.append(Space(number + 1, self.players[number // 16]))
            else:
                self.spaces.append(Space(number + 1))
        for number in range(32):
            self.spaces.append(Space(number + 65, self.players[(number // 4) % len(self.players)]))
    
    def detectPlayers(self):
        self.players.append(Player()) #ToDo: append active players