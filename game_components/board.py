from space import Space
from player import Player
from deck import Deck

class Board:
    spaces = []

    def __init__(self, players):
        self.players = players
        self.fillSpaces()
    
    def fillSpaces(self):
        for number in range(64):
            if number % 17 == 0:
                self.spaces.append(Space(number + 1, self.players[number // 17]))
            else:
                self.spaces.append(Space(number + 1))
        for number in range(32):
            self.spaces.append(Space(number + 65, self.players[(number // 4) % len(self.players)]))

    def update(self, pawn, steps, switch = False):
        self.spaces[pawn.position].occupiedBy = None
        currentPawn = self.spaces[pawn.position + steps].occupiedBy
        if currentPawn and not switch:
            currentPawn.position = currentPawn.basePosition
            currentPawn.inPlay = False
        self.spaces[pawn.position + steps].occupiedBy = pawn
    
