class Pawn:
    def __init__(self, owner, id):
        self.owner = owner
        self.id = id
        self.basePosition = 80 + (int(owner) * 4) + id
        self.position = self.basePosition
        self.inPlay = False
        self.startSpace = int(owner) * 17
        self.endZoneStart = 64 + (int(owner) * 4)

    def updatePosition(self, steps):
        self.position = self.position + steps