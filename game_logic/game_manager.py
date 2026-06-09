import asyncio
from game_components.board import Board
from game_components.card import Card
from game_logic.move import movePawn
from game_components.player import Player
from connection.communication import CommunicationManager

class GameManager:
    
    def __init__(self, communication_manager: CommunicationManager, event_loop=None):
        self.players = []
        self.current_player_index = 0
        self.board = None
        self.comm = communication_manager or CommunicationManager()
        self.game_started = False
        self.event_loop = event_loop  # Store reference to main event loop

    def handleEvent(self, event):
        t = event["type"]

        if t == "PLAYER_JOIN" and not self.game_started:
            player_id = event.get("player_id")
            if player_id is None:
                return
            if not any(p.id == player_id for p in self.players):
                self.players.append(Player("player" + str(player_id), player_id))

        elif t == "CONFIRM_START":
            self.startGame()

        elif t == "CARD_PLAYED":
            self.playCard(
                event["player_id"],
                event.get("card"),
                event.get("pion_id"),
                event.get("pion2_id"),
                event.get("movePawn2"),
                event.get("discard", False)
            )
    
    def startGame(self):
        """Start the game and notify all connected clients (WebSocket and USB serials)"""
        if self.game_started:
            return
        
        if len(self.players) < 2 or len(self.players) > 4:
            return
        
        self.game_started = True
        self.board = Board(self.players)

        # Initialize game logic here
        self.checkAndRedealCards()
        
        # Notify all connected WebSocket and USB serial devices
        current_player_id = self.players[self.current_player_index].id
        self.broadcast(self.comm.broadcast_current_turn(current_player_id))


    def getPlayerById(self, player_id):
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def playCard(self, player_id, card_data, pawn_id, pawn2_id=None, movePawn2=None, discard=False):
        # Validate it's the current player's turn by comparing IDs (not index)
        current_player_id = self.players[self.current_player_index].id
        if player_id != current_player_id:
            print(f"Not player {player_id}'s turn (current is {current_player_id})")
            self.broadcast(self.comm.send_player_error(player_id, "Niet jouw beurt"))
            return

        player = self.getPlayerById(player_id)
        if player is None:
            print(f"Unknown player {player_id}")
            return

        # Properly handle card_data - could be Card object or dict
        if isinstance(card_data, Card):
            card = card_data
        else:
            # card_data is a dict with "face" key
            face = card_data.get("face") if isinstance(card_data, dict) else str(card_data)
            card = Card(face)

        if discard:
            print(f"Player {player_id} discarded card {card.face}")
            # Mark card as empty (15) instead of removing it
            self.markCardAsEmpty(player, card)
            # Send updated hand to player
            self.broadcast(self.comm.broadcast_hand(player.id, player.cards))
            # Switch turns
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            next_player_id = self.players[self.current_player_index].id
            self.broadcast(self.comm.broadcast_current_turn(next_player_id))
            for other_player in self.players:
                self.broadcast(self.comm.broadcast_player_positions(other_player))
            # Check if all hands are empty and redeal if needed
            self.checkAndRedealCards()
            return

        if pawn_id is None or pawn_id < 0 or pawn_id >= len(player.pawns):
            print(f"Invalid pawn id {pawn_id} from player {player_id}")
            self.broadcast(self.comm.send_player_error(player_id, "Ongeldige pion"))
            return

        pawn = player.pawns[pawn_id]
        pawn2 = None
        if pawn2_id is not None and 0 <= int(pawn2_id) < len(player.pawns):
            pawn2 = player.pawns[int(pawn2_id)]

        success = movePawn(self.board, card, pawn, pawn2, movePawn2)
        if not success:
            print(f"Invalid move by player {player_id} with card {card.face}")
            self.broadcast(self.comm.send_player_error(player_id, "Ongeldige zet"))
            return

        print(f"Player {player_id} played {card.face} on pawn {pawn_id}")
        
        # Mark card as empty (15) instead of removing it
        self.markCardAsEmpty(player, card)
        
        # Broadcast pawn position updates to all players
        for other_player in self.players:
            self.broadcast(self.comm.broadcast_player_positions(other_player))
        
        # Send updated hand to the player who just played
        self.broadcast(self.comm.broadcast_hand(player_id, player.cards))

        # Check if all hands are empty and redeal if needed
        self.checkAndRedealCards()

        # Switch to next player's turn
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        next_player_id = self.players[self.current_player_index].id
        self.broadcast(self.comm.broadcast_current_turn(next_player_id))

    def markCardAsEmpty(self, player, card):
        """Mark a card in player's hand as empty (15). Marks first matching card by face value."""
        for hand_card in player.cards:
            if hand_card.face == card.face:
                hand_card.face = "15"
                print(f"Marked card {card.face} as empty (15) for player {player.id}")
                return
        print(f"Warning: Card {card.face} not found in player {player.id}'s hand")

    def checkAndRedealCards(self):
        """Check if all players have all empty cards (15) and redeal if true"""
        all_hands_empty = all(all(card.face == "15" for card in player.cards) for player in self.players) or all(len(player.cards) == 0 for player in self.players)
        if all_hands_empty and self.board and self.board.deck:
            print("All players' hands are empty. Redealing cards...")
            self.board.deck.dealCards()
            for player in self.players:
                self.broadcast(self.comm.broadcast_hand(player.id, player.cards))

    def broadcast(self, message):
        """Send async message safely from game loop thread"""
        if self.event_loop and self.event_loop.is_running():
            # Schedule coroutine in the main event loop from this thread
            return asyncio.run_coroutine_threadsafe(message, self.event_loop)
        else:
            # Fallback: create and run event loop in current thread
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(message)
                return result
            except Exception as e:
                print(f"Error broadcasting: {e}")