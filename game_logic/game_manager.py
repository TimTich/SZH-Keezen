import asyncio
from game_components.board import Board
from game_components.deck import Deck
from game_components.card import Card
from game_logic.move import movePawn
from game_components.player import Player
from connection.communication import CommunicationManager

class GameManager:
    
    def __init__(self, communication_manager: CommunicationManager):
        self.players = []
        self.current_player_index = 0
        self.board = None
        self.deck = None
        self.comm = communication_manager or CommunicationManager()
        self.game_started = False

    def _create_async_task(self, coro):
        """Helper to safely create async tasks even from sync context"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            print("No running event loop, task not created")

    def handleEvent(self, event):
        t = event["type"]
        print(f"Game Manager: Processing event type '{t}'")

        if t == "PLAYER_JOIN" and not self.game_started:
            player_id = event["player_id"]
            print(f"PLAYER_JOIN received for player {player_id}")
            if not any(p.id == player_id for p in self.players):
                self.players.append(Player("player" + str(player_id), player_id))
                print(f"Player {player_id} added. Total players: {len(self.players)}")
            if event.get("_websocket"):
                self.comm.register_websocket_player(event["_websocket"], player_id)
            
            # Broadcast het huidige spelerenaantal naar iedereen
            self._create_async_task(self.broadcast_player_count())

        elif t == "CONFIRM_START":
            self.startGame()

        elif t == "CARD_PLAYED":
            self.playCard(
                event.get("player_id"),
                event.get("card"),
                event.get("pion_id"),
                event.get("pion2_id"),
                event.get("movePawn2")
            )
    
    async def broadcast_player_count(self):
        """Broadcast the current player count to all connected clients"""
        message = {
            "type": "PLAYER_COUNT",
            "player_count": len(self.players)
        }
        await self.comm._broadcast_websocket(message)
    
    async def broadcast_current_player(self):
        """Broadcast which player is allowed to play next."""
        message = {
            "type": "CURRENT_PLAYER",
            "player_id": self.current_player_index
        }
        await self.comm._broadcast_websocket(message)
    
    def startGame(self):
        if self.game_started:
            return
        if len(self.players) < 4:
            print(f"Spel kan nog niet starten! Wachten op minimaal 4 spelers. (Huidig: {len(self.players)})")
            for player in self.players:
                self._create_async_task(self.comm.send_player_message(player.id, {
                    "type": "FOUT_ZET",
                    "bericht": "Nog niet genoeg spelers verbonden; het spel start niet."
                }))
            return
        
        print(f"Starting game with {len(self.players)} players...")
        self.current_player_index = 0
        self.game_started = True
        self.board = Board(self.players)
        self.deck = Deck(self.players)
        self.deck.dealCards()

        try:
            self._create_async_task(self.comm.broadcast_game_start())
            self._create_async_task(self.broadcast_current_player())
        except Exception as e:
            print(f"Error broadcasting game start: {e}")

        for player in self.players:
            self._create_async_task(self.comm.send_player_message(player.id, {
                "type": "NIEUWE_HAND",
                "kaarten": [card.face for card in player.cards]
            }))
            self._create_async_task(self.comm.send_player_message(player.id, {
                "type": "UPDATE_BORD",
                "pionnen": self.get_board_state_for_player(player)
            }))


        print("Game initialized and notifications sent")

    def playCard(self, player_id, card_data, pawn_id, pawn2_id=None, movePawn2=None):
        if player_id != self.current_player_index:
            self._create_async_task(self.comm.send_player_message(player_id, {
                "type": "FOUT_ZET",
                "bericht": "Het is niet jouw beurt."
            }))
            return

        player = next((p for p in self.players if p.id == player_id), None)
        if player is None:
            print(f"Unknown player {player_id}")
            return

        if pawn_id is None or pawn_id < 0 or pawn_id >= len(player.pawns):
            self._create_async_task(self.comm.send_player_message(player_id, {
                "type": "FOUT_ZET",
                "bericht": "Geen geldige pion geselecteerd."
            }))
            return

        pawn = player.pawns[pawn_id]
        pawn2 = None
        if pawn2_id is not None and 0 <= pawn2_id < len(player.pawns):
            pawn2 = player.pawns[pawn2_id]

        card = Card(card_data["face"])
        success = movePawn(self.board, card, pawn, pawn2, movePawn2)

        if not success:
            self._create_async_task(self.comm.send_player_message(player_id, {
                "type": "FOUT_ZET",
                "bericht": "Ongeldige zet. Probeer een andere pion of kaart."
            }))
            return

        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self._create_async_task(self.broadcast_current_player())
        for player in self.players:
            self._create_async_task(self.comm.send_player_message(player.id, {
                "type": "UPDATE_BORD",
                "pionnen": self.get_board_state_for_player(player)
            }))

    def format_pawn_label(self, pawn):
        if pawn.position >= 80 and pawn.position <= 95:
            return "b"
        if pawn.position >= 64 and pawn.position <= 79:
            return "e"
        if pawn.position == pawn.basePosition and not pawn.inPlay:
            return "B"

        label = str(pawn.position)
        if pawn.entry_card_face and pawn.inPlay:
            label += pawn.entry_card_face
        return label

    def get_board_state_for_player(self, player):
        state = {}
        for index, pawn in enumerate(player.pawns, start=1):
            state[f"pion-{index}"] = self.format_pawn_label(pawn)
        return state