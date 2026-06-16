import json
import threading
from typing import List, Dict, Optional
from queue import Queue

try:
    import serial
except Exception:
    serial = None
    print("pyserial niet gevonden; USB-ondersteuning uitgeschakeld.")

class CommunicationManager:
    """Manages communication with WebSocket clients and USB serial devices"""
    
    def __init__(self, event_queue: Optional[Queue] = None):
        self.websocket_clients: List = []
        self.websocket_player_map: Dict = {}
        self.usb_player_map: Dict[str, int] = {}
        self.usb_serials: Dict[str, serial.Serial] = {}
        self.usb_player_map: Dict = {}  # NIEUW: Koppelt player_id aan een USB-poort
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
            self.websocket_player_map.pop(client, None)
            print(f"WebSocket client disconnected. Total clients: {len(self.websocket_clients)}")

    def register_websocket_player(self, client, player_id):
        """Link a websocket client to a player ID"""
        if client in self.websocket_clients:
            self.websocket_player_map[client] = player_id
            print(f"WebSocket client registered for player {player_id}")

    def register_usb_player(self, port: str, player_id: int):
        """NIEUW: Link een fysieke Arduino USB-poort aan een player ID"""
        self.usb_player_map[player_id] = port
        print(f"USB Serial port {port} geregistreerd voor player {player_id}")

    def get_player_websocket(self, player_id):
        """Return the connected websocket client for a given player ID."""
        for client, pid in self.websocket_player_map.items():
            if pid == player_id:
                return client
        return None

    def get_player_usb(self, player_id):
        """Return the USB serial port for a given player ID."""
        for port, pid in self.usb_player_map.items():
            if pid == player_id:
                return port
        return None

    def register_usb_player(self, port: str, player_id: int):
        """Link a USB serial port to a player ID."""
        if port in self.usb_serials:
            self.usb_player_map[port] = player_id
            print(f"USB serial port {port} registered for player {player_id}")

    def get_all_mapped_player_ids(self):
        """Return all player IDs currently mapped to sockets or USB devices."""
        player_ids = set(self.websocket_player_map.values())
        player_ids.update(self.usb_player_map.values())
        return player_ids

    async def _send_websocket_message(self, client, message: Dict):
        """Send a JSON message to a single websocket client."""
        try:
            await client.send(json.dumps(message))
        except Exception as e:
            print(f"Error sending message to websocket client: {e}")
            self.remove_websocket_client(client)

    async def send_player_message(self, player_id, message: Dict):
        """UPGRADE: Stuurt berichten naar de juiste bron (WebSocket óf Fysieke Arduino)"""
        client = self.get_player_websocket(player_id)
        if client:
            # Stuur naar de telefoon/iPad van de speler
            await self._send_websocket_message(client, message)
        elif player_id in self.usb_player_map:
            # NIEUW: Stuur direct naar de Arduino (voor het flapdisplay / lampjes)
            port = self.usb_player_map[player_id]
            ser = self.usb_serials.get(port)
            if ser:
                try:
                    message["target_player_id"] = player_id
                    message_str = json.dumps(message) + "\n"
                    ser.write(message_str.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending to USB serial on {port}: {e}")
        else:
            print(f"No active connection found for player {player_id}")
    
    def register_usb_serial(self, port: str, baudrate: int = 9600) -> bool:
        """Register a USB serial connection"""
        if serial is None:
            print("Cannot register USB serial: pyserial not installed")
            return False
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            self.usb_serials[port] = ser
            print(f"USB serial connected on port {port}")
            return True
        except Exception as e:
            print(f"Failed to connect to USB serial on {port}: {e}")
            return False
    
    def disconnect_usb_serial(self, port: str) -> bool:
        """Disconnect a USB serial connection"""
        if port in self.usb_serials:
            try:
                self.usb_serials[port].close()
                del self.usb_serials[port]
                self.usb_player_map.pop(port, None)
                print(f"USB serial disconnected from port {port}")
                return True
            except Exception as e:
                print(f"Error disconnecting USB serial on {port}: {e}")
                return False
        return False
    
    def set_event_queue(self, event_queue: Queue):
        """Set or update the event queue for incoming messages"""
        self.event_queue = event_queue
    
    async def listen_websocket_message(self, client, message: str):
        """Handle incoming WebSocket message and add to event queue"""
        try:
            event = json.loads(message)
            event["_websocket"] = client
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
                            
                            try:
                                event = json.loads(buffer)
                                # FIX: Voeg het _port stempel toe, net zoals bij websockets!
                                event["_port"] = port
                                if self.event_queue:
                                    event["_usb_port"] = port
                                    self.event_queue.put(event)
                                else:
                                    print("Warning: No event queue configured for incoming messages")
                                buffer = ""
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    print(f"Serial read error on {port}: {e}")
                    break
        
        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
        self.usb_listener_threads[port] = thread
    
    def stop_usb_listeners(self):
        """Stop all USB serial listener threads"""
        self.stop_listening = True
        for port, thread in self.usb_listener_threads.items():
            if thread.is_alive():
                thread.join(timeout=2)
    
    async def broadcast_game_start(self):
        """Broadcast game start message to all connected WebSocket clients and USB serials"""
        message = {
            "type": "GAME_START",
            "status": "GAME_STARTED"
        }
        await self._broadcast_websocket(message)
        self._broadcast_usb_serial(message)
    
    async def _broadcast_websocket(self, message: Dict):
        """Send message to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
        disconnected_clients = []
        for client in self.websocket_clients:
            try:
                await client.send(json.dumps(message))
            except Exception as e:
                disconnected_clients.append(client)
        for client in disconnected_clients:
            self.remove_websocket_client(client)
    
    def _broadcast_usb_serial(self, message: Dict):
        """Send message to all connected USB serial devices"""
        if not self.usb_serials:
            return
        message_str = json.dumps(message) + "\n"
        message_bytes = message_str.encode('utf-8')
        for port, ser in self.usb_serials.items():
            try:
                ser.write(message_bytes)
            except Exception as e:
                print(f"Error broadcasting to USB serial on {port}: {e}")
    
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
