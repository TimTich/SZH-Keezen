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
            pass

    def handleEvent(self, event):
        t = event["type"]
        if t == "PLAYER_JOIN" and not self.game_started:
            player_id = event.get("player_id")
            existing_ids = {p.id for p in self.players}
            
            if player_id is None:
                free_id = next((i for i in range(4) if i not in existing_ids), None)
                if free_id is None:
                    return
                player_id = free_id
            
            if player_id not in existing_ids:
                self.players.append(Player("player" + str(player_id), player_id))
            
            if event.get("_websocket"):
                self.comm.register_websocket_player(event["_websocket"], player_id)
                self._create_async_task(self.comm.send_player_message(player_id, {
                    "type": "ASSIGNED_PLAYER_ID",
                    "player_id": player_id
                }))
                
            self._create_async_task(self.broadcast_player_count())

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
                if pawn.inPlay and pawn.position < 64 and pawn.position != pawn.startSpace:
                    is_valid = True
                
                status[str(p.id)].append({
                    "id": i,
                    "label": self.format_pawn_label(pawn),
                    "is_valid": is_valid
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
            kaart_waardes = [card.face for card in player.cards]
            bericht = {"type": "NIEUWE_HAND", "kaarten": kaart_waardes}
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
        
        # === NIEUW: Check voor onspeelbare Boer ===
        if card.face == "J":
            alle_pionnen = self.get_all_pawns_status()
            has_own = any(p["is_valid"] for p in alle_pionnen.get(str(player.id), []))
            has_enemy = any(any(p["is_valid"] for p in pawns) for pid, pawns in alle_pionnen.items() if pid != str(player.id))
            
            # Als hij echt niet gespeeld kan worden...
            if not has_own or not has_enemy:
                has_ace_or_king = any(c.face in ("A", "K") for c in player.cards)
                has_unplayed_pawn = any(not p.inPlay for p in player.pawns)
                
                if has_ace_or_king and has_unplayed_pawn:
                    # Speler wordt gedwongen in het spel te komen
                    self._create_async_task(self.comm.send_player_message(player_id, {"type": "FOUT_ZET", "bericht": "Je kunt de Boer niet spelen. Je moet eerst een Aas of Koning spelen."}))
                    return
                else:
                    # Gooi hem geruisloos in de prullenbak
                    card_to_remove = next((c for c in player.cards if c.face == card.face), None)
                    if card_to_remove: player.cards.remove(card_to_remove)
                    self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
                    self.endTurn()
                    return
        # ==========================================

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
                card_to_remove = next((c for c in player.cards if c.face == card.face), None)
                if card_to_remove: player.cards.remove(card_to_remove)
                
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

        card_to_remove = next((c for c in player.cards if c.face == card.face), None)
        if card_to_remove: player.cards.remove(card_to_remove)

        self._create_async_task(self.comm.send_player_message(player_id, {"type": "MOVE_SUCCEEDED"}))
        self.endTurn()

    def endTurn(self):
        if all(len(p.cards) == 0 for p in self.players):
            self.sub_round += 1
            if self.sub_round > 3:
                self.sub_round = 1
                self.grand_round += 1
                self.starting_player_index = (self.starting_player_index + 1) % len(self.players)
                self.deck.shuffle()
            
            deal_amount = 5 if self.sub_round == 1 else 4
            self.deck.dealCards(deal_amount)
            self.current_player_index = self.starting_player_index
            self.broadcast_hands()
        else:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            
        self._create_async_task(self.broadcast_current_player())
        self.broadcast_game_state()