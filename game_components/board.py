from game_components.space import Space
from game_components.player import Player
from game_components.deck import Deck

class Board:
    spaces = []

    def __init__(self, players):
        self.players = players
        self.fillSpaces()
    
    def fillSpaces(self):
        for number in range(64):
            if number % 17 == 0 and self.players:
                owner_index = (number // 17) % len(self.players)
                self.spaces.append(Space(number + 1, self.players[owner_index]))
            else:
                self.spaces.append(Space(number + 1))
        for number in range(32):
            owner_index = (number // 4) % len(self.players) if self.players else 0
            self.spaces.append(Space(number + 65, self.players[owner_index] if self.players else None))

    def update(self, pawn, steps, switch = False):
        self.spaces[pawn.position].occupiedBy = None
        currentPawn = self.spaces[pawn.position + steps].occupiedBy
        if currentPawn and not switch:
            currentPawn.position = currentPawn.basePosition
            currentPawn.inPlay = False
            currentPawn.clear_entry_card()
        self.spaces[pawn.position + steps].occupiedBy = pawn
    
