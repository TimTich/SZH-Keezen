def movePawn(board, card, pawn, pawn2 = None, movePawn2 = None):
    if card.face == "7"  and pawn2 and movePawn2:
        return splitSeven(board, pawn, pawn2, movePawn2)
    elif card.face == "J" and pawn and pawn2:
        return switch(board, pawn, pawn2)
    elif (card.face == "K" or card.face == "A") and (not pawn.inPlay):
        return enterPlay(board, pawn)
    elif (card.face == "4") and pawn.inPlay:
        steps = getSteps(card);
        return moveBack(board, steps, pawn)
    elif (not card.face == "J") and (not card.face == "K") and pawn.inPlay:
        steps = getSteps(card);
        return moveOnePawn(board, steps, pawn)
    else:
        return False

def moveOnePawn(board, steps, pawn):
    if checkMove(board, pawn, steps + 1):
        board.update(pawn, steps)
        pawn.updatePosition(steps)
        return True
    return False

def moveBack(board, steps, pawn):
    if checkMove(board, pawn, steps - 1, -1):
        board.update(pawn, steps)
        pawn.updatePosition(steps)
        return True
    return False

def splitSeven(board, pawn, pawn2, movePawn2):
    pawn1Steps = 7 - movePawn2
    if checkMove(board, pawn2, movePawn2 + 1) and checkMove(board, pawn, pawn1Steps + 1):
        board.update(pawn, pawn1Steps)
        pawn.updatePosition(pawn1Steps)
        board.update(pawn2, movePawn2)
        pawn2.updatePosition(movePawn2)
        return True
    return False

def switch(board, pawn, pawn2):
    if checkMove(board, pawn, 0) and checkMove(board, pawn2, 0):
        tempPosition = pawn.position
        pawn.position = pawn2.position
        pawn2.position = tempPosition
        board.update(pawn, 0, True)
        board.update(pawn2, 0, True)
        return True
    return False

def enterPlay(board, pawn):
    pawn.position = pawn.startSpace
    if checkMove(board, pawn, 0):
        board.update(pawn, 0)
        pawn.inPlay = True
        return True
    pawn.position = pawn.basePosition
    return False

def checkMove(board, pawn, steps, direction = 1):
    endZone = pawn.position <= 80 and pawn.position >= 64;
    stepsTaken = 0
    id = None
    start = 1
    if direction == -1:
        start = -1
    for step in range(start, steps, direction):
        if endZone:
            if pawn.endZoneStart + stepsTaken >= len(board.spaces) or step - stepsTaken > 4:
                return False
            space = board.spaces[pawn.endZoneStart + (step - stepsTaken)]
            print(f"Checking end zone space {space.number} for pawn {pawn.id} with step {step} and stepsTaken {stepsTaken}")
            if step == steps - 1:
                return True
                
        else:
            space = board.spaces[(pawn.position + step) % 64]
            print(f"Checking board space {space.number} for pawn {pawn.id} with step {step} and stepsTaken {stepsTaken}")
        if space.number == (pawn.startSpace - 1) % 64:
            endZone = True
            stepsTaken = step
            print(f"Pawn {pawn.id} has entered the end zone, switching to end zone spaces")
        if space.owner:
            id = space.owner.id
        if (space.occupied_by and space.occupied_by.owner == id): #No check for end zone yet
            print(f"Move blocked by pawn {space.occupied_by.id} owned by player {id} at space {space.number}")
            return False
    return True

def getSteps(card):
    if (card.face == "4"):
        return -4
    elif (card.face == "A"):
        return 1
    elif (card.face == "Q"):
        return 14
    else:
        return int(card.face)