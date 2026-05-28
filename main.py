import asyncio
import queue
import threading
import webbrowser
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from connection.communication import CommunicationManager
from connection.websocket import start_websocket_server
from game_logic import game_loop
from game_logic.game_manager import GameManager


def start_static_http_server(port: int = 8000, directory: str = "interface") -> HTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Static UI server running at http://localhost:{port}")
    return server

# --- DIT BLOKJE HEB JE NODIG OM DE MOTOR TE LATEN DRAAIEN ---
async def async_game_loop(g_loop):
    """Een speciale loop die de Pi continu laat nadenken zonder vast te lopen"""
    while True:
        g_loop.processEvents()
        await asyncio.sleep(0.01)

async def main():
    event_queue = queue.Queue()
    comm_manager = CommunicationManager(event_queue=event_queue)
    
    # Register USB devices (Geeft op een Mac een kleine waarschuwing, maar stopt de code niet)
    comm_manager.register_usb_serial("COM3", baudrate=9600)
    comm_manager.listen_usb_serial("COM3")
    
    # Start de statische UI-server zodat index.html vanuit Python bereikbaar is
    start_static_http_server(port=8000, directory="interface")
    # Open vier browser tabs naar dezelfde lokale UI
    for _ in range(4):
        webbrowser.open_new_tab("http://localhost:8000")

    # Start WebSocket server op de achtergrond
    websocket_task = asyncio.create_task(start_websocket_server(comm_manager))

    # Maak de manager en de loop aan
    gameManager = GameManager(communication_manager=comm_manager)
    gameLoop = game_loop.GameLoop(gameManager, event_queue)

    # --- ZET DE MOTOR AAN! ---
    asyncio.create_task(async_game_loop(gameLoop))
    print("De Game Motor draait...")

    # Zorg dat het programma oneindig blijft draaien
    await websocket_task

if __name__ == "__main__":
    asyncio.run(main())