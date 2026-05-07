from pawn import Pawn

class Player:
    def __init__(self, name, player_id):
        self.name = name
        self.id = player_id
        self.pawns = [Pawn(player_id) for _ in range(4)]
        self.cards = []