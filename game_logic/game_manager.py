import asyncio
from game_components.board import Board
from game_components.deck import Deck
from game_components.card import Card
from game_logic.move import movePawn, bereken_route, getSteps
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
            pass

    def _register_connection_for_player(self, event, player_id):
        """Register the incoming connection for the given player ID."""
        if event.get("_websocket"):
            self.comm.register_websocket_player(event["_websocket"], player_id)
        if event.get("_usb_port"):
            self.comm.register_usb_player(event["_usb_port"], player_id)

        if event.get("_websocket") or event.get("_usb_port"):
            self._create_async_task(self.comm.send_player_message(player_id, {
                "type": "ASSIGNED_PLAYER_ID",
                "player_id": player_id
            }))

    def _resolve_join_player_id(self, event, max_players=4):
        """Resolve a unique player ID for a join event without causing collisions."""
        requested_id = event.get("player_id")
        try:
            requested_id = int(requested_id) if requested_id is not None else None
        except (TypeError, ValueError):
            requested_id = None

        mapped_ids = self.comm.get_all_mapped_player_ids()

        if requested_id is not None:
            already_mapped = requested_id in mapped_ids
            if not already_mapped:
                return requested_id

            # Allow reconnect from the same websocket or USB device for the same ID.
            if event.get("_websocket"):
                existing_ws = self.comm.get_player_websocket(requested_id)
                if existing_ws == event["_websocket"]:
                    return requested_id
            if event.get("_usb_port"):
                existing_port = self.comm.get_player_usb(requested_id)
                if existing_port == event["_usb_port"]:
                    return requested_id

        return next((i for i in range(max_players) if i not in mapped_ids), None)

    def handleEvent(self, event):
        t = event["type"]
        if t == "PLAYER_JOIN":
            player_id = self._resolve_join_player_id(event)

            if player_id is None:
                return

            if not self.game_started:
                # Spel is nog niet gestart: voeg spelers normaal toe
                existing_ids = {p.id for p in self.players}
                if player_id not in existing_ids:
                    self.players.append(Player("player" + str(player_id), player_id))

                self._register_connection_for_player(event, player_id)
                self._create_async_task(self.broadcast_player_count())
            else:
                # FIX: Het spel is al gestart! Koppel de telefoon direct aan een vrije speler-positie
                if player_id >= len(self.players):
                    return

                self._register_connection_for_player(event, player_id)
                self.broadcast_hands()
                self.broadcast_game_state()
                self._create_async_task(self.broadcast_current_player())

        elif t == "CONFIRM_START":
            self.startGame()

        elif t == "CARD_PLAYED":
            self.playCard(
                event.get("player_id"),
                event.get("card"),
                event.get("pion_id"),
                event.get("pion2_id"),
                event.get("movePawn2"),
                event.get("target_player_id")
            )
            
        elif t == "DISCARD_CARD":
            self.discardCard(event.get("player_id"), event.get("card"))

    def check_win(self, player):
        for pawn in player.pawns:
            if not (64 <= pawn.position <= 79):
                return False
        return True

    def is_card_playable(self, player, card):
        if card.face == "gespeeld": return False
        
        if card.face in ("A", "K"):
            for pawn in player.pawns:
                if not pawn.inPlay:
                    start_space = self.board.spaces[pawn.startSpace]
                    bezetter = getattr(start_space, 'occupied_by', None)
                    if bezetter is None or int(bezetter.owner) != int(player.id):
                        return True
            if card.face == "A":
                for pawn in player.pawns:
                    if pawn.inPlay:
                        geldig, _ = bereken_route(self.board, pawn, 1)
                        if geldig: return True
                return False

        elif card.face == "J":
            alle_pionnen = self.get_all_pawns_status()
            has_own = any(p["is_valid_own"] for p in alle_pionnen.get(str(player.id), []))
            has_enemy = any(any(p["is_valid"] for p in pawns) for pid, pawns in alle_pionnen.items() if pid != str(player.id))
            return has_own and has_enemy

        elif card.face == "7":
            total_possible_steps = 0
            for pawn in player.pawns:
                if pawn.inPlay:
                    max_steps = 0
                    for s in range(1, 8):
                        geldig, _ = bereken_route(self.board, pawn, s)
                        if geldig: max_steps = s
                    total_possible_steps += max_steps
            return total_possible_steps >= 7

        else:
            steps = getSteps(card)
            for pawn in player.pawns:
                if pawn.inPlay:
                    geldig, _ = bereken_route(self.board, pawn, steps)
                    if geldig: return True
            return False

    def discardCard(self, player_id, card_data):
        try: player_id = int(player_id)
        except (TypeError, ValueError): return

        current_player = self.players[self.current_player_index]
        if player_id != current_player.id:
            self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Het is niet jouw beurt."}))
            return

        player = next((p for p in self.players if p.id == player_id), None)
        if player is None: return

        card = Card(card_data["face"])
        
        if self.is_card_playable(player, card):
            self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Ongeldig! Deze kaart kan nog gewoon gespeeld worden."}))
            return

        card_to_remove = next((c for c in player.cards if c.face == card.face and c.face != "gespeeld"), None)
        if card_to_remove:
            card_to_remove.face = "gespeeld"
            self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
            self.endTurn()
    
    async def broadcast_player_count(self):
        message = {"type": "PLAYER_COUNT", "player_count": len(self.players)}
        await self.comm._broadcast_websocket(message)
    
    async def broadcast_current_player(self):
        if not self.players: return
        message = {"type": "CURRENT_PLAYER", "player_id": self.players[self.current_player_index].id}
        await self.comm._broadcast_websocket(message)

    def format_pawn_label(self, pawn):
        if pawn.position >= 80: return "B"
        if 64 <= pawn.position <= 79:
            stap = (pawn.position % 4) + 1
            return f"E{stap}"
        return str(pawn.position + 1)

    def get_all_pawns_status(self):
        status = {}
        for p in self.players:
            status[str(p.id)] = []
            for i, pawn in enumerate(p.pawns):
                is_valid = False
                is_valid_own = False
                
                if pawn.inPlay and pawn.position < 64:
                    is_valid_own = True 
                    if pawn.position != pawn.startSpace:
                        is_valid = True 
                
                status[str(p.id)].append({
                    "id": i,
                    "label": self.format_pawn_label(pawn),
                    "is_valid": is_valid,
                    "is_valid_own": is_valid_own
                })
        return status

    def broadcast_game_state(self):
        alle_pionnen = self.get_all_pawns_status()
        
        for player in self.players:
            pionnen_status = {}
            for i, pawn in enumerate(player.pawns):
                pion_id_naam = f"pion-{i + 1}"
                pionnen_status[pion_id_naam] = self.format_pawn_label(pawn)
            
                update_bericht = { 
                    "type": "UPDATE_BORD", 
                    "pionnen": pionnen_status,
                    "alle_pionnen": alle_pionnen
                }
                self._create_async_task(self.comm.send_player_message(player.id, update_bericht))
    
    def broadcast_hands(self):
        for player in self.players:
            kaart_waardes = []
            weggooi_opties = {}
            
            for card in player.cards:
                kaart_waardes.append(card.face)
                if card.face != "gespeeld":
                    speelbaar = self.is_card_playable(player, card)
                    weggooi_opties[card.face] = not speelbaar
                else:
                    weggooi_opties[card.face] = False

            bericht = {
                "type": "NIEUWE_HAND",
                "kaarten": kaart_waardes,
                "weggooi_opties": weggooi_opties
            }
            self._create_async_task(self.comm.send_player_message(player.id, bericht))

    def startGame(self):
        if self.game_started or len(self.players) < 2: return
        
        self.players.sort(key=lambda player: player.id)
        
        self.grand_round = 1
        self.sub_round = 1
        self.starting_player_index = 0
        self.current_player_index = self.starting_player_index
        
        self.game_started = True
        self.board = Board(self.players)
        self.deck = Deck(self.players)
        
        for p in self.players:
            p.cards = []
            
        self.deck.dealCards(5)

        self._create_async_task(self.comm._broadcast_websocket({"type": "GAME_START", "status": "GAME_STARTED"}))
        self._create_async_task(self.broadcast_current_player())
        self.broadcast_hands()
        self.broadcast_game_state()

    def playCard(self, player_id, card_data, pawn_id, pawn2_id=None, movePawn2=None, target_player_id=None):
        try: player_id = int(player_id)
        except (TypeError, ValueError): return

        current_player = self.players[self.current_player_index]
        if player_id != current_player.id:
            self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Het is niet jouw beurt."}))
            return

        player = next((p for p in self.players if p.id == player_id), None)
        if player is None or pawn_id is None or pawn_id < 0 or pawn_id >= len(player.pawns): return

        pawn = player.pawns[pawn_id]
        pawn2 = None
        card = Card(card_data["face"])
        
        if card.face == "gespeeld": return

        if card.face == "J":
            alle_pionnen = self.get_all_pawns_status()
            
            has_own = any(p["is_valid_own"] for p in alle_pionnen.get(str(player.id), []))
            has_enemy = any(any(p["is_valid"] for p in pawns) for pid, pawns in alle_pionnen.items() if pid != str(player.id))
            
            if not has_own or not has_enemy:
                has_ace_or_king = any(c.face in ("A", "K") for c in player.cards)
                has_unplayed_pawn = any(not p.inPlay for p in player.pawns)
                
                if has_ace_or_king and has_unplayed_pawn:
                    self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Je kunt de Boer niet spelen. Je moet eerst een Aas of Koning spelen."}))
                    return
                else:
                    card_to_remove = next((c for c in player.cards if c.face == card.face and c.face != "gespeeld"), None)
                    if card_to_remove: card_to_remove.face = "gespeeld"
                    self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
                    self.endTurn()
                    return

        if card.face == "J" and target_player_id is not None:
            try:
                target_player = next((p for p in self.players if p.id == int(target_player_id)), None)
                if target_player and pawn2_id is not None:
                    pawn2 = target_player.pawns[int(pawn2_id)]
            except (ValueError, TypeError):
                pass
        elif pawn2_id is not None:
            try:
                p2_id_int = int(pawn2_id)
                if 0 <= p2_id_int < len(player.pawns):
                    pawn2 = player.pawns[p2_id_int]
            except (ValueError, TypeError):
                pass 
        
        if not pawn.inPlay and card.face not in ("A", "K"):
            has_ace_or_king = any(c.face in ("A", "K") for c in player.cards)
            if not has_ace_or_king:
                card_to_remove = next((c for c in player.cards if c.face == card.face and c.face != "gespeeld"), None)
                if card_to_remove: card_to_remove.face = "gespeeld"
                self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
                self.endTurn()
                return
            else:
                self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Je moet eerst een Aas of Koning spelen."}))
                return

        success = movePawn(self.board, card, pawn, pawn2, movePawn2)

        if not success:
            self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Ongeldige zet."}))
            return

        card_to_remove = next((c for c in player.cards if c.face == card.face and c.face != "gespeeld"), None)
        if card_to_remove: card_to_remove.face = "gespeeld"

        self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
        
        if self.check_win(player):
            self.board.spaces[pawn.position].occupied_by = pawn
            self.broadcast_game_state()
            self._create_async_task(self.comm._broadcast_websocket({"type": "GAME_WON", "player_id": player.id}))
            return

        self.endTurn()

    def endTurn(self):
        ronde_klaar = True
        for p in self.players:
            for c in p.cards:
                if c.face != "gespeeld":
                    ronde_klaar = False
                    break
            if not ronde_klaar:
                break
                
        if ronde_klaar:
            self.sub_round += 1
            if self.sub_round > 3:
                self.sub_round = 1
                self.grand_round += 1
                self.starting_player_index = (self.starting_player_index + 1) % len(self.players)
                self.deck.shuffle()
            
            deal_amount = 5 if self.sub_round == 1 else 4
            for p in self.players:
                p.cards = []
                
            self.deck.dealCards(deal_amount)
            self.current_player_index = self.starting_player_index
        else:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            
        self.broadcast_hands()
        self._create_async_task(self.broadcast_current_player())
        self.broadcast_game_state()