import asyncio
from game_components.board import Board
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
                print("PLAYER_JOIN event missing player_id")
                return
            if any(p.id == player_id for p in self.players):
                print(f"Player {player_id} already joined")
            else:
                self.players.append(Player("player" + str(player_id), player_id))

        elif t == "CONFIRM_START":
            self.startGame()

        elif t == "CARD_PLAYED":
            self.playCard(
                event["player_id"],
                event["card"],
                event["pawn"]
            )
    
    def startGame(self):
        """Start the game and notify all connected clients (WebSocket and USB serials)"""
        if self.game_started:
            print("Game already started")
            return
        
        if len(self.players) < 2 or len(self.players) > 4:
            print(f"Cannot start game: need at least 2 players and maximum 4 players, but only {len(self.players)} are connected")
            return
        
        print(f"Starting game with {len(self.players)} players...")
        self.game_started = True
        self.board = Board(self.players)
        
        # Initialize game logic here
        self.dealCards()

        # Notify all connected WebSocket and USB serial devices
        self.broadcast(self.comm.broadcast_game_start())

    def dealCards(self):
        """Deal cards to all players from the deck and send them to each player"""
        if self.board and self.board.deck:
            self.board.deck.dealCards()
            print(f"Registered players: {[p.id for p in self.players]}")
            print(f"Available websocket_clients: {list(self.comm.websocket_clients)}")
            
            # Send each player their hand
            for player in self.players:
                print(f"Sending cards to player {player.id}: {[card.face for card in player.cards]}")
                self.broadcast(self.comm.broadcast_hand(player.id, player.cards))
        else:
            print("Error: Board or deck not initialized")

    def playCard(self, player_id, card, pawn):
        if player_id == self.current_player_index:
            movePawn(self.board, card, pawn)
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            for player in self.players:
                self.broadcast(self.comm.broadcast_turn_end(player))

    def broadcast(self, message):
        """Send async message safely from game loop thread"""
        if self.event_loop and self.event_loop.is_running():
            # Schedule coroutine in the main event loop from this thread
            asyncio.run_coroutine_threadsafe(message, self.event_loop)
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
                loop.run_until_complete(message)
            except Exception as e:
                print(f"Error broadcasting: {e}")