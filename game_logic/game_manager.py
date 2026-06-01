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
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            print("No running event loop, task not created")

    def handleEvent(self, event):
        t = event["type"]
        print(f"💬 [BERICHT BINNEN IN PYTHON]: {t}")
        
        if t == "PLAYER_JOIN" and not self.game_started:
            player_id = event["player_id"]
            existing_ids = {p.id for p in self.players}
            
            # FIX: Voorkom spook-spelers! Als de speler de pagina ververst, maak dan geen nieuwe stoel aan.
            if player_id not in existing_ids:
                self.players.append(Player("player" + str(player_id), player_id))
                print(f"✅ Speler {player_id} is verbonden. Totaal aan tafel: {len(self.players)}")
            else:
                print(f"🔄 Speler {player_id} is opnieuw verbonden (Pagina ververst). Teller blijft: {len(self.players)}")

            if event.get("_websocket"):
                self.comm.register_websocket_player(event["_websocket"], player_id)
            
            self._create_async_task(self.broadcast_player_count())

        elif t == "CONFIRM_START":
            print("🚀 'SPEEL' KNOP INGEDRUKT! Startcommando succesvol ontvangen.")
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
        message = {
            "type": "PLAYER_COUNT",
            "player_count": len(self.players)
        }
        await self.comm._broadcast_websocket(message)
    
    async def broadcast_current_player(self):
        if not self.players:
            return
        message = {
            "type": "CURRENT_PLAYER",
            "player_id": self.players[self.current_player_index].id
        }
        await self.comm._broadcast_websocket(message)

    def format_pawn_label(self, pawn):
        if pawn.position >= 80:
            return "B"
        if 64 <= pawn.position <= 79:
            stap = (pawn.position % 4) + 1
            return f"E{stap}"
        return str(pawn.position)

    def broadcast_game_state(self):
        pionnen_status = {}
        for player in self.players:
            for i, pawn in enumerate(player.pawns):
                pion_id_naam = f"pion-{(player.id * 4) + i + 1}"
                pionnen_status[pion_id_naam] = self.format_pawn_label(pawn)

        update_bericht = { "type": "UPDATE_BORD", "pionnen": pionnen_status }
        self._create_async_task(self.comm._broadcast_websocket(update_bericht))
    
    def broadcast_hands(self):
        for player in self.players:
            kaart_waardes = [card.face for card in player.cards]
            bericht = {
                "type": "NIEUWE_HAND",
                "kaarten": kaart_waardes
            }
            self._create_async_task(self.comm.send_player_message(player.id, bericht))

    def startGame(self):
        if self.game_started:
            print("⚠️ Het spel was al gestart. Extra klik genegeerd.")
            return
        if len(self.players) < 2:
            print(f"❌ Kan niet starten! Er zijn maar {len(self.players)} spelers.")
            return
        
        print(f"🏁 Bord wordt opgebouwd voor {len(self.players)} spelers...")
        self.players.sort(key=lambda player: player.id)
        starting_player_id = 0 if any(player.id == 0 for player in self.players) else self.players[0].id
        self.current_player_index = next((index for index, player in enumerate(self.players) if player.id == starting_player_id), 0)
        
        self.game_started = True
        self.board = Board(self.players)
        self.deck = Deck(self.players)
        self.deck.dealCards()

        print("📡 Kaarten en bord worden verstuurd naar de schermen...")
        self._create_async_task(self.comm._broadcast_websocket({
            "type": "GAME_START",
            "status": "GAME_STARTED"
        }))

        self._create_async_task(self.broadcast_current_player())
        self.broadcast_hands()
        self.broadcast_game_state()
        print("✅ Spel is succesvol en foutloos gestart!")

    def playCard(self, player_id, card_data, pawn_id, pawn2_id=None, movePawn2=None):
        try:
            player_id = int(player_id)
        except (TypeError, ValueError):
            return

        current_player = self.players[self.current_player_index]
        if player_id != current_player.id:
            self._create_async_task(self.comm.send_player_message(player_id, {
                "type": "FOUT_ZET",
                "bericht": "Het is niet jouw beurt."
            }))
            return

        player = next((p for p in self.players if p.id == player_id), None)
        if player is None:
            return

        if pawn_id is None or pawn_id < 0 or pawn_id >= len(player.pawns):
            return

        pawn = player.pawns[pawn_id]
        pawn2 = None
        if pawn2_id is not None and 0 <= pawn2_id < len(player.pawns):
            pawn2 = player.pawns[pawn2_id]

        card = Card(card_data["face"])
        
        if not pawn.inPlay and card.face not in ("A", "K"):
            has_ace_or_king = any(c.face in ("A", "K") for c in player.cards)
            if not has_ace_or_king:
                self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
                self._create_async_task(self.comm.send_player_message(player_id, {"type": "FLIP_ALL_CARDS"}))
                self.current_player_index = (self.current_player_index + 1) % len(self.players)
                self._create_async_task(self.broadcast_current_player())
                self.broadcast_game_state()
                return
            else:
                self._create_async_task(self.comm.send_player_message(player_id, {
                    "type": "FOUT_ZET",
                    "bericht": "Je moet eerst een Aas of Koning spelen om deze pion in te kunnen zetten."
                }))
                return

        success = movePawn(self.board, card, pawn, pawn2, movePawn2)

        if not success:
            self._create_async_task(self.comm.send_player_message(player_id, {
                "type": "FOUT_ZET",
                "bericht": "Ongeldige zet. Probeer een andere pion of kaart."
            }))
            return

        self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self._create_async_task(self.broadcast_current_player())
        self.broadcast_game_state()