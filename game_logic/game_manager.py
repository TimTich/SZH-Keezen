import asyncio
from game_components.board import Board
from game_logic.move import movePawn
from game_components.player import Player
from connection.communication import CommunicationManager

class GameManager:
    
    def __init__(self, communication_manager: CommunicationManager):
        self.players = []
        self.current_player_index = 0
        self.board = None
        self.comm = communication_manager or CommunicationManager()
        self.game_started = False

    def handleEvent(self, event):
        t = event["type"]

        if t == "PLAYER_JOIN" and not self.game_started:
            self.players.append(Player("player" + str(event["player_id"]), event["player_id"]))

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
        
        if len(self.players) < 2:
            print(f"Cannot start game: need at least 2 players, but only {len(self.players)} are connected")
            return
        
        print(f"Starting game with {len(self.players)} players...")
        self.game_started = True
        self.board = Board(self.players)
        
        # Notify all connected WebSocket and USB serial devices
        try:
            # Create a new event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the broadcast coroutine
            loop.run_until_complete(self.comm.broadcast_game_start())
        except Exception as e:
            print(f"Error broadcasting game start: {e}")
            # Even if broadcast fails, continue with game logic
        
        # Initialize game logic here
        print("Game initialized and notifications sent")

    def playCard(self, player_id, card, pawn):
        if player_id == self.current_player_index:
            movePawn(self.board, card, pawn)
            self.current_player_index = (self.current_player_index + 1) % len(self.players)