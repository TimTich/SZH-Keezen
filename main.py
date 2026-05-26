import asyncio
import queue
from connection.communication import CommunicationManager
from game_logic import game_loop
from game_manager import GameManager


async def main():
    event_queue = queue.Queue()
    comm_manager = CommunicationManager(event_queue=event_queue)
    # Register USB devices
    comm_manager.register_usb_serial("COM3", baudrate=9600)
    comm_manager.listen_usb_serial("COM3")
    
    # Start WebSocket server
    websocket_task = asyncio.create_task(start_websocket_server())
 
    # Start game loop in a separate thread (or use async version)
    gameManager = GameManager(communication_manager=comm_manager)
    gameLoop = game_loop.GameLoop(gameManager, event_queue)

    await websocket_task

if __name__ == "__main__":
    asyncio.run(main())