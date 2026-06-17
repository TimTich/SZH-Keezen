import asyncio
import queue
import sys
import threading
import webbrowser
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from connection.communication import CommunicationManager
from connection.websocket import start_websocket_server
from game_logic import game_loop
from game_logic.game_manager import GameManager

# FIX: directory="." vertelt hem dat hij in de hoofdmap moet zoeken
def start_static_http_server(port: int = 8000, directory: str = "interface") -> HTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Static UI server running at http://localhost:{port} (Kijkt nu in de hoofdmap!)")
    return server

async def async_game_loop(g_loop):
    while True:
        g_loop.processEvents()
        await asyncio.sleep(0.01)

async def main():
    event_queue = queue.Queue()
    comm_manager = CommunicationManager(event_queue=event_queue)
    
    if sys.platform.startswith("win"):
        port = "COM3"
    else:
        port = "/dev/ttyACM0"

    comm_manager.register_usb_serial(port, baudrate=9600)
    comm_manager.listen_usb_serial(port)
    
# Start de statische UI-server zodat index.html vanuit Python bereikbaar is
    start_static_http_server(port=8000, directory="interface") 

    websocket_task = asyncio.create_task(start_websocket_server(comm_manager))

    gameManager = GameManager(communication_manager=comm_manager)
    gameLoop = game_loop.GameLoop(gameManager, event_queue)

    asyncio.create_task(async_game_loop(gameLoop))
    print("De Game Motor draait...")

    await websocket_task

if __name__ == "__main__":
    asyncio.run(main())
   