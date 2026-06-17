from game_components.space import Space

class Board:
    def __init__(self, players):
        self.players = players
        self.spaces = []
        self.fillSpaces()
    
    def fillSpaces(self):
        player_dict = {p.id: p for p in self.players}

        for number in range(64):
            # FIX: Aangepast van 17 naar 16
            if number % 16 == 0:
                expected_id = number // 16
                index = 0 if expected_id == 0 else 2 if expected_id == 1 else 1 if expected_id == 2 else 3
                owner = player_dict.get(index, None)
                self.spaces.append(Space(number + 1, owner))
            else:
                self.spaces.append(Space(number + 1))
                
        for number in range(32):
            expected_id = (number // 4) % 4
            index = 0 if expected_id == 0 else 2 if expected_id == 1 else 1 if expected_id == 2 else 3
            owner = player_dict.get(index, None)
            pawn = owner.pawns[number // 4 % 4] if owner and number >= 16 else None
            self.spaces.append(Space(number + 65, owner, pawn))

    def update(self, pawn, steps, switch = False):
        self.spaces[pawn.position].occupied_by = None
        
        target_space = self.spaces[pawn.position + steps]
        currentPawn = target_space.occupied_by
        
        if currentPawn and not switch:
            currentPawn.position = currentPawn.basePosition
            currentPawn.inPlay = False
            currentPawn.clear_entry_card()
            
        target_space.occupied_by = pawn

    def getPlayerSpaces(self):
        player_spaces = []
        for space in self.spaces:
            if space.occupied_by and space.occupied_by.owner is not None:
                player_spaces.append(int(space.occupied_by.owner))
            else:
                player_spaces.append(4)
        return player_spaces
        