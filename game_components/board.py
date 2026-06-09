from game_components.space import Space
from game_components.player import Player
from game_components.deck import Deck

class Board:
    spaces = []

    def __init__(self, players):
        self.players = players
        self.fillSpaces()
        self.deck = Deck(players)
    
    def fillSpaces(self):
        for number in range(64):
            if number % 17 == 0 and number // 17 < len(self.players):
                self.spaces.append(Space(number + 1, self.players[number // 17]))
            else:
                self.spaces.append(Space(number + 1))
        for number in range(32):
            player = None
            if number // 4 < len(self.players):
                 player = self.players[(number // 4) % 4]
            self.spaces.append(Space(number + 65, player))

    def update(self, pawn, steps, switch = False):
        self.spaces[pawn.position].occupied_by = None
        currentPawn = self.spaces[(pawn.position + steps) % 64].occupied_by
        if currentPawn and not switch:
            currentPawn.position = currentPawn.basePosition
            currentPawn.inPlay = False
        self.spaces[(pawn.position + steps) % 64].occupied_by = pawn
    
