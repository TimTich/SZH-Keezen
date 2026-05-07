from card import Card
import random

class Deck:
    cards = []

    def __init__(self, players):
        self.players = players
        self.shuffle()
    
    def schuffle(self):
        self.addCards()
        random.shuffle(self.cards)
    
    def addCards(self):
        for face in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10' 'J', 'Q', 'K']:
            for _ in self.players:
                self.cards.append(Card(face))

    def dealCards(self, amount):
        for _ in range(amount):
            for player in self.players:
                player.cards.append(self.cards.pop())