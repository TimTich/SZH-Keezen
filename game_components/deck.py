from game_components.card import Card
import random

class Deck:
    cards = []
    max_cards = None;

    def __init__(self, players):
        self.players = players
        self.shuffle()
    
    def shuffle(self):
        self.addCards()
        random.shuffle(self.cards)
    
    def addCards(self):
        for face in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']:
            for _ in self.players:
                self.cards.append(Card(face))
        self.max_cards = len(self.cards)

    def dealCards(self):

        if len(self.cards) == 0:
            self.shuffle()
        amount = None
        if self.max_cards == len(self.cards):
            amount = 5
        else:
            amount = 4
        for index in range(amount):
            for player in self.players:
                if index == 0:
                    player.cards = []
                player.cards.append(self.cards.pop())