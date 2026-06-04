from game_components.card import Card
import random

class Deck:
    def __init__(self, players):
        self.players = players
        self.cards = [] 
        self.max_cards = 0
        self.shuffle()
    
    def shuffle(self):
        self.cards = [] # Verwijder oude kaarten voor de zekerheid
        self.addCards()
        random.shuffle(self.cards)
    
    def addCards(self):
        for face in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']:
            for _ in self.players:
                self.cards.append(Card(face))
        self.max_cards = len(self.cards)

    def dealCards(self, amount):
        for _ in range(amount):
            for player in self.players:
                if self.cards:
                    player.cards.append(self.cards.pop())