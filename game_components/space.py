class Space:
    def __init__(self, number, owner=None, occupied_by=None):
        self.number = number
        self.owner = owner
        self.occupied_by = occupied_by