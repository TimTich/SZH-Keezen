def movePawn(board, card, pawn, pawn2=None, movePawn2=None):
    if card.face == "7" and pawn2 and movePawn2:
        return splitSeven(board, pawn, pawn2, movePawn2)
    elif card.face == "J" and pawn and pawn2:
        return switch(board, pawn, pawn2)
    elif (card.face == "K" or card.face == "A") and (not pawn.inPlay):
        return enterPlay(board, pawn, card.face)
    elif card.face != "J" and pawn.inPlay:
        steps = getSteps(card)
        return moveOnePawn(board, steps, pawn)
    else:
        return False

def enterPlay(board, pawn, card_face=None):
    dest_index = pawn.startSpace
    dest_space = board.spaces[dest_index]
    
    bezetter = getattr(dest_space, 'occupied_by', None)
    if bezetter is not None:
        if int(bezetter.owner) == int(pawn.owner):
            return False 
        else:
            bezetter.position = bezetter.basePosition
            bezetter.inPlay = False
            bezetter.clear_entry_card()
    
    print (pawn.position)
    if pawn.position >= 80:
        board.spaces[pawn.position].occupied_by = None
    print (board.spaces[pawn.position].occupied_by)
        
    
    pawn.position = dest_index
    dest_space.occupied_by = pawn
    pawn.inPlay = True
    pawn.entry_card_face = card_face
    return True

def moveOnePawn(board, steps, pawn):
    geldig, doel_index = bereken_route(board, pawn, steps)
    if geldig and doel_index is not None:
        voer_zet_uit(board, pawn, doel_index)
        return True
    return False
    
def splitSeven(board, pawn, pawn2, movePawn2):
    pawn1Steps = 7 - movePawn2
    geldig1, doel1 = bereken_route(board, pawn, pawn1Steps)
    geldig2, doel2 = bereken_route(board, pawn2, movePawn2)
    
    if geldig1 and geldig2 and doel1 is not None and doel2 is not None:
        voer_zet_uit(board, pawn, doel1)
        voer_zet_uit(board, pawn2, doel2)
        return True
    return False

# DE FIX: Deze functie ruilt puur de posities om zonder de ander "dood" te maken.
def switch(board, pawn, pawn2):
    if pawn.inPlay and pawn2.inPlay:
        if pawn.position >= 64 or pawn2.position >= 64:
            return False

        space1 = board.spaces[pawn.position]
        space2 = board.spaces[pawn2.position]

        if space2.owner is not None and int(pawn2.owner) == space2.owner.id:
            return False

        # Directe wiskundige ruil
        tempPosition = pawn.position
        pawn.position = pawn2.position
        pawn2.position = tempPosition
        
        board.spaces[pawn.position].occupied_by = pawn
        board.spaces[pawn2.position].occupied_by = pawn2
        return True
    return False

def voer_zet_uit(board, pawn, doel_index):
    board.spaces[pawn.position].occupied_by = None
    target_space = board.spaces[doel_index]
    currentPawn = target_space.occupied_by
    
    if currentPawn:
        board.spaces[currentPawn.basePosition].occupied_by = currentPawn
        currentPawn.position = currentPawn.basePosition
        currentPawn.inPlay = False
        currentPawn.clear_entry_card()
        
    target_space.occupied_by = pawn
    pawn.position = doel_index

def bereken_route(board, pawn, steps):
    if steps == 0:
        return True, pawn.position

    if steps < 0:
        if pawn.position >= 64:
            return False, None
            
        doel = (pawn.position + steps) % 64
        space = board.spaces[doel]
        bezetter = getattr(space, 'occupied_by', None)
        if bezetter is not None:
            if space.owner is not None and int(bezetter.owner) == space.owner.id:
                return False, None
            if int(bezetter.owner) == int(pawn.owner):
                return False, None
        return True, doel

    huidige_pos = pawn.position
    is_endzone = False
    endzone_stap = 0
    
    if huidige_pos >= 64:
        is_endzone = True
        endzone_stap = huidige_pos - pawn.endZoneStart
    
    for step in range(steps):
        if not is_endzone:
            afslag_index = (pawn.startSpace - 1) % 64
            if huidige_pos == afslag_index:
                is_endzone = True
                huidige_pos = pawn.endZoneStart
                endzone_stap = 0
            else:
                huidige_pos = (huidige_pos + 1) % 64
        else:
            endzone_stap += 1
            huidige_pos = pawn.endZoneStart + endzone_stap
            if endzone_stap > 3:
                return False, None
                
        space = board.spaces[huidige_pos]
        bezetter = getattr(space, 'occupied_by', None)
        if bezetter is not None:
            if space.owner is not None and int(bezetter.owner) == space.owner.id:
                return False, None
                
            if step == steps - 1:
                if int(bezetter.owner) == int(pawn.owner):
                    return False, None
            else:
                if is_endzone:
                    return False, None
        
    return True, huidige_pos

def getSteps(card):
    if (card.face == "4"): return -4
    elif (card.face == "A"): return 1
    elif (card.face == "Q"): return 12
    elif (card.face == "K"): return 0
    else: return int(card.face)