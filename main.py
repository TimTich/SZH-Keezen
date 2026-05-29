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


def start_static_http_server(port: int = 8000, directory: str = "interface") -> HTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    for candidate_port in range(port, port + 10):
        try:
            server = HTTPServer(("0.0.0.0", candidate_port), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            print(f"Static UI server running at http://localhost:{candidate_port}")
            return server
        except OSError as e:
            if e.errno == 48:
                print(f"Poort {candidate_port} is in gebruik, probeer volgende... ")
                continue
            raise
    raise OSError(f"Geen vrije poort gevonden tussen {port} en {port + 9}")

# --- DIT BLOKJE HEB JE NODIG OM DE MOTOR TE LATEN DRAAIEN ---
async def async_game_loop(g_loop):
    """Een speciale loop die de Pi continu laat nadenken zonder vast te lopen"""
    while True:
        g_loop.processEvents()
        await asyncio.sleep(0.01)

async def main():
    event_queue = queue.Queue()
    comm_manager = CommunicationManager(event_queue=event_queue)
    
    # Alleen Windows gebruikt COM3 als USB seriële poort
    if sys.platform.startswith("win"):
        comm_manager.register_usb_serial("COM3", baudrate=9600)
        comm_manager.listen_usb_serial("COM3")
    else:
        print("USB serial wordt overgeslagen op dit systeem; alleen Windows gebruikt COM3.")
    
    # Start de statische UI-server zodat index.html vanuit Python bereikbaar is
    server = start_static_http_server(port=8000, directory="interface")
    webbrowser.open(f"http://localhost:{server.server_port}")

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