class Pawn:
    def __init__(self, owner, id):
        self.owner = owner
        self.id = id
        multiplier = 0 if owner == 0 else 2 if owner == 1 else 1 if owner == 2 else 3
        self.basePosition = 80 + (multiplier * 4) + id
        self.position = self.basePosition
        self.inPlay = False
        # FIX: Aangepast van 17 naar 16 (64 vakjes / 4 spelers)
        self.startSpace = multiplier * 16 
        self.endZoneStart = 64 + (multiplier * 4)
        self.entry_card_face = None

    def updatePosition(self, steps):
        self.position = self.position + steps

    def clear_entry_card(self):
        self.entry_card_face = None