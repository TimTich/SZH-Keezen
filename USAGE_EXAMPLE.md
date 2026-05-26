"""
Usage Example: Game Start Logic with Communication Manager

This shows how to integrate the GameManager with CommunicationManager
for bidirectional communication with WebSocket and USB serial clients.
"""

import queue
import asyncio
from game_logic.game_manager import GameManager
from game_logic.communication import CommunicationManager
from game_logic.game_loop import GameLoop

# Create event queue for incoming messages
event_queue = queue.Queue()

# Initialize the communication manager with the event queue
comm_manager = CommunicationManager(event_queue=event_queue)

# Register USB serial devices (adjust ports based on your system)
# comm_manager.register_usb_serial("COM3", baudrate=9600)
# comm_manager.register_usb_serial("COM4", baudrate=9600)

# Start listening for incoming USB serial messages
# comm_manager.listen_usb_serial("COM3")
# comm_manager.listen_usb_serial("COM4")

# Initialize the game manager with the communication manager
game_manager = GameManager(communication_manager=comm_manager)

# Create game loop
game_loop = GameLoop(game_manager, event_queue)

# ============================================
# WEBSOCKET SERVER INTEGRATION EXAMPLE
# ============================================
# import websockets
# 
# async def websocket_handler(websocket, path):
#     """Handle WebSocket connections"""
#     comm_manager.add_websocket_client(websocket)
#     try:
#         async for message in websocket:
#             # Pass incoming message to the listener
#             await comm_manager.listen_websocket_message(websocket, message)
#     except Exception as e:
#         print(f"WebSocket error: {e}")
#     finally:
#         comm_manager.remove_websocket_client(websocket)
#
# async def start_websocket_server():
#     """Start WebSocket server on localhost:8765"""
#     async with websockets.serve(websocket_handler, "localhost", 8765):
#         await asyncio.Future()  # Run forever

# ============================================
# EVENT EXAMPLES
# ============================================
# 
# 1. Player joins (from WebSocket or USB):
#    {"type": "PLAYER_JOIN", "player_id": 1}
#
# 2. Confirm start (triggers broadcast to all clients):
#    {"type": "CONFIRM_START"}
#
# 3. Card played (from player):
#    {"type": "CARD_PLAYED", "player_id": 1, "card": "card_name"}
#
# 4. UI request state:
#    {"type": "UI_REQUEST_STATE"}

# ============================================
# WORKFLOW
# ============================================
# 
# 1. WebSocket/USB clients send events as JSON strings
# 2. CommunicationManager receives and parses them
# 3. Events are added to the event_queue
# 4. GameLoop processes events via GameManager.handleEvent()
# 5. When "CONFIRM_START" is received:
#    - GameManager.startGame() is called
#    - CommunicationManager broadcasts to all connected clients:
#      {"type": "GAME_START", "status": "GAME_STARTED"}
# 6. Game continues, players send more events

# ============================================
# STARTUP EXAMPLE
# ============================================
# 
# async def main():
#     # Register USB devices
#     comm_manager.register_usb_serial("COM3", baudrate=9600)
#     comm_manager.listen_usb_serial("COM3")
#     
#     # Start WebSocket server
#     websocket_task = asyncio.create_task(start_websocket_server())
#     
#     # Start game loop in a separate thread (or use async version)
#     game_loop.start()
#     
#     await websocket_task
#
# if __name__ == "__main__":
#     asyncio.run(main())

# ============================================
# CLEANUP
# ============================================
# 
# When shutting down:
# comm_manager.cleanup()  # Stops listeners, disconnects USB, clears WebSocket clients
