from player import Player

class GameManager:
    players = []

    def __init__(self):
        pass

    def detectPlayers(self):
        self.players.append(Player("player1", 1)) #ToDo: append active players