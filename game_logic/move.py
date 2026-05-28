def movePawn(board, card, pawn, pawn2 = None, movePawn2 = None):
    if card.face == "7"  and pawn2 and movePawn2:
        return splitSeven(board, pawn, pawn2, movePawn2)
    elif card.face == "J" and pawn and pawn2:
        return switch(board, pawn, pawn2)
    elif (card.face == "K" or card.face == "A") and (not pawn.inPlay):
        return enterPlay(board, pawn, card.face)
    elif (not card.face == "J") and (not card.face == "K") and pawn.inPlay:
        steps = getSteps(card);
        return moveOnePawn(board, steps, pawn)
    else:
        return False

def moveOnePawn(board, steps, pawn):
    if checkMove(board, pawn, steps):
        board.update(pawn, steps)
        pawn.updatePosition(steps)
    return False

def splitSeven(board, pawn, pawn2, movePawn2):
    pawn1Steps = 7 - movePawn2
    if checkMove(board, pawn2, movePawn2) and checkMove(board, pawn, pawn1Steps):
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

def enterPlay(board, pawn, card_face=None):
    pawn.position = pawn.startSpace
    if checkMove(board, pawn, 0):
        board.update(pawn, 0)
        pawn.inPlay = True
        pawn.entry_card_face = card_face
        return True
    pawn.position = pawn.basePosition
    return False

def checkMove(board, pawn, steps):
    endZone = False;
    stepsTaken = 0
    for step in range(steps):
        if endZone:
            if pawn.endZoneStart + stepsTaken >= len(board.spaces) or step - stepsTaken > 4:
                return False
            space = board.spaces[pawn.endZoneStart + stepsTaken]
        else:
            space = board.spaces[(pawn.position + step) % 64]
        if space.number == pawn.startSpace - 1 or (space.number == 64 and pawn.owner == 0):
            endZone = True
            stepsTaken = step
        if (space.occuiedBy and space.occupiedBy.owner == space.owner.id): #No check for end zone yet
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