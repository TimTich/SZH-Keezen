class Pawn:
    def __init__(self, owner, id):
        self.owner = owner
        self.id = id
        multiplier = 3 if owner == 0 else 1 if owner == 1 else 0 if owner == 2 else 2
        self.basePosition = 80 + (multiplier * 4) + id
        self.position = self.basePosition
        self.inPlay = False
        self.startSpace = (multiplier * 16) - 1
        self.endZoneStart = 64 + (multiplier * 4)
        self.entry_card_face = None

    def updatePosition(self, steps):
        self.position = self.position + steps

    def clear_entry_card(self):
        self.entry_card_face = None