import json
import serial
import threading
from typing import List, Dict, Optional
from queue import Queue

class CommunicationManager:
    """Manages communication with WebSocket clients and USB serial devices"""
    
    def __init__(self, event_queue: Optional[Queue] = None):
        self.websocket_clients: List = []
        self.player_clients: Dict[int, any] = {} # type: ignore
        self.usb_serials: Dict[str, serial.Serial] = {}
        self.event_queue = event_queue
        self.usb_listener_threads: Dict[str, threading.Thread] = {}
        self.stop_listening = False
    
    def add_websocket_client(self, client):
        """Register a new WebSocket client"""
        if client not in self.websocket_clients:
            self.websocket_clients.append(client)
            print(f"WebSocket client connected. Total clients: {len(self.websocket_clients)}")
    
    def remove_websocket_client(self, client):
        """Unregister a WebSocket client"""
        if client in self.websocket_clients:
            self.websocket_clients.remove(client)
            print(f"WebSocket client disconnected. Total clients: {len(self.websocket_clients)}")

        for player_id, websocket_client in list(self.player_clients.items()):
            if websocket_client == client:
                del self.player_clients[player_id]
                print(f"Unregistered player {player_id} from websocket client")
    
    def register_usb_serial(self, port: str, baudrate: int = 9600) -> bool:
        """Register a USB serial connection"""
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            self.usb_serials[port] = ser
            print(f"USB serial connected on port {port}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to USB serial on {port}: {e}")
            return False
    
    def disconnect_usb_serial(self, port: str) -> bool:
        """Disconnect a USB serial connection"""
        if port in self.usb_serials:
            try:
                self.usb_serials[port].close()
                del self.usb_serials[port]
                print(f"USB serial disconnected from port {port}")
                return True
            except Exception as e:
                print(f"Error disconnecting USB serial on {port}: {e}")
                return False
        return False
    
    def set_event_queue(self, event_queue: Queue):
        """Set or update the event queue for incoming messages"""
        self.event_queue = event_queue
    
    def _assign_player_id(self):
        """Assign the next available player ID based on join order."""
        for candidate in range(4):
            if candidate not in self.player_clients:
                return candidate
        return None

    async def listen_websocket_message(self, client, message: str):
        """Handle incoming WebSocket message and add to event queue"""
        try:
            event = json.loads(message)
            if event.get("type") == "PLAYER_JOIN":
                assigned_id = self._assign_player_id()
                if assigned_id is None:
                    error_message = {
                        "type": "PLAYER_ASSIGNMENT_FAILED",
                        "reason": "Maximum number of players reached"
                    }
                    await client.send(json.dumps(error_message))
                    print("Rejected PLAYER_JOIN because maximum players are already connected")
                    return

                event["player_id"] = assigned_id
                self.player_clients[assigned_id] = client
                print(f"Registered player {assigned_id} to websocket client")
                await client.send(json.dumps({
                    "type": "PLAYER_ASSIGNED",
                    "player_id": assigned_id
                }))

            if self.event_queue:
                self.event_queue.put(event)
                print(f"Added WebSocket event to queue: {event['type']}")
            else:
                print("Warning: No event queue configured for incoming messages")
        except json.JSONDecodeError as e:
            print(f"Error parsing WebSocket message: {e}")
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
    
    def listen_usb_serial(self, port: str):
        """Listen for incoming messages on a USB serial port"""
        if port not in self.usb_serials:
            print(f"USB serial port {port} not registered")
            return
        
        ser = self.usb_serials[port]
        print(f"Starting USB serial listener on port {port}")
        
        def _listen():
            buffer = ""
            while not self.stop_listening:
                try:
                    if ser.in_waiting:
                        data = ser.readline()
                        message = data.decode('utf-8').strip()
                        
                        if message:
                            buffer += message
                            
                            # Try to parse as JSON when we get a complete message
                            try:
                                event = json.loads(buffer)
                                if self.event_queue:
                                    self.event_queue.put(event)
                                    print(f"Added USB serial event from {port} to queue: {event['type']}")
                                else:
                                    print("Warning: No event queue configured for incoming messages")
                                buffer = ""
                            except json.JSONDecodeError:
                                # Message not complete yet, continue buffering
                                pass
                except serial.SerialException as e:
                    print(f"Serial error on {port}: {e}")
                    break
                except Exception as e:
                    print(f"Error reading from USB serial on {port}: {e}")
        
        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
        self.usb_listener_threads[port] = thread
    
    def stop_usb_listeners(self):
        """Stop all USB serial listener threads"""
        self.stop_listening = True
        for port, thread in self.usb_listener_threads.items():
            if thread.is_alive():
                thread.join(timeout=2)
                print(f"Stopped listener thread for {port}")
    
    async def broadcast_game_start(self):
        """Broadcast game start message to all connected WebSocket clients and USB serials"""
        message = {
            "type": "GAME_START",
            "status": "GAME_STARTED"
        }
        
        # Debug: show connected clients and player mapping
        try:
            print(f"DEBUG: Broadcasting GAME_START. websocket_clients={len(self.websocket_clients)}, player_clients={list(self.player_clients.keys())}")
        except Exception:
            pass

        # First, send directly to registered player websocket clients (per-player)
        if self.player_clients:
            for pid, client in list(self.player_clients.items()):
                try:
                    await client.send(json.dumps(message))
                    print(f"Sent GAME_START to player {pid}")
                except Exception as e:
                    print(f"Error sending GAME_START to player {pid}: {e}")

        # Also broadcast to any remaining websocket clients (fallback)
        await self._broadcast_websocket(message)
        
        # Send to USB serials
        self._broadcast_usb_serial(message)

    async def broadcast_turn_end(self, player):
        """Broadcast turn end message to all connected WebSocket clients and USB serials"""
        message = {
            "type": "TURN_END",
            "status": "TURN_ENDED",
            "player_id": player.player_id,
            "pawn 1": player.pawns[0].position,
            "pawn 2": player.pawns[1].position,
            "pawn 3": player.pawns[2].position,
            "pawn 4": player.pawns[3].position
        }
        
        # Send to WebSocket clients
        await self._broadcast_websocket(message)
        
        # Send to USB serials
        self._broadcast_usb_serial(message)

    async def broadcast_hand(self, player_id, cards):
        """Broadcast dealt hand to a specific player"""
        # Convert card objects to their face values (strings)
        card_faces = [card.face for card in cards]
        
        message = {
            "type": "NIEUWE_HAND",
            "kaarten": card_faces
        }
        
        print(f"DEBUG: Trying to send hand to player {player_id}")
        print(f"DEBUG: Available players in player_clients: {list(self.player_clients.keys())}")
        
        message_json = json.dumps(message)
        if player_id in self.player_clients:
            try:
                await self.player_clients[player_id].send(message_json)
                print(f"Sent hand to player {player_id}: {card_faces}")
                return
            except Exception as e:
                print(f"Error sending hand to player {player_id}: {e}")

        print(f"Warning: Player {player_id} not found in player_clients. Falling back to broadcast to all connected websockets.")
        await self._broadcast_websocket(message)
    
    
    async def _broadcast_websocket(self, message: Dict):
        """Send message to all connected WebSocket clients"""
        if not self.websocket_clients:
            print("No WebSocket clients connected")
            return
        
        message_json = json.dumps(message)  # Send as string, not bytes
        disconnected_clients = []
        
        for client in self.websocket_clients:
            try:
                await client.send(message_json)
                print(f"Sent message to WebSocket client: {message['type']}")
            except Exception as e:
                print(f"Error sending to WebSocket client: {e}")
                disconnected_clients.append(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            self.remove_websocket_client(client)
    
    def _broadcast_usb_serial(self, message: Dict):
        """Send message to all connected USB serial devices"""
        if not self.usb_serials:
            print("No USB serial devices connected")
            return
        
        message_str = json.dumps(message) + "\n"
        message_bytes = message_str.encode('utf-8')
        
        for port, ser in self.usb_serials.items():
            try:
                ser.write(message_bytes)
                print(f"Sent game start message to USB serial on port {port}")
            except serial.SerialException as e:
                print(f"Error sending to USB serial on {port}: {e}")
    
    def get_connection_status(self) -> Dict:
        """Get current connection status"""
        return {
            "websocket_clients": len(self.websocket_clients),
            "usb_serials": list(self.usb_serials.keys()),
            "active_listeners": list(self.usb_listener_threads.keys())
        }
    
    def cleanup(self):
        """Clean up all connections and threads"""
        self.stop_usb_listeners()
        
        for port in list(self.usb_serials.keys()):
            self.disconnect_usb_serial(port)
        
        self.websocket_clients.clear()
        print("CommunicationManager cleaned up")
