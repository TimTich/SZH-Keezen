from game_components.space import Space

class Board:
    def __init__(self, players):
        self.players = players
        self.spaces = []
        self.fillSpaces()
    
    def fillSpaces(self):
        # We maken een woordenboekje om spelers makkelijk op hun ID op te zoeken
        player_dict = {p.id: p for p in self.players}

        for number in range(64):
            if number % 17 == 0:
                expected_id = number // 17
                owner = player_dict.get(expected_id, None)
                self.spaces.append(Space(number + 1, owner))
            else:
                self.spaces.append(Space(number + 1))
                
        for number in range(32):
            expected_id = (number // 4) % 4
            owner = player_dict.get(expected_id, None)
            self.spaces.append(Space(number + 65, owner))

    def update(self, pawn, steps, switch = False):
        self.spaces[pawn.position].occupied_by = None
        
        target_space = self.spaces[pawn.position + steps]
        currentPawn = target_space.occupied_by
        
        if currentPawn and not switch:
            currentPawn.position = currentPawn.basePosition
            currentPawn.inPlay = False
            currentPawn.clear_entry_card()
            
        target_space.occupied_by = pawn