class Space:
    def __init__(self, number, owner=None):
        self.number = number
        self.owner = owner
        self.occupied_by = None