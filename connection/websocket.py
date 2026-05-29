import asyncio

try:
    import websockets
except Exception:
    websockets = None


def create_websocket_handler(comm_manager):
    """Create a WebSocket handler with comm_manager bound to it"""
    async def websocket_handler(websocket):
        comm_manager.add_websocket_client(websocket)
        print(f"New WebSocket client connected. Clients: {len(comm_manager.websocket_clients)}")
        try:
            async for message in websocket:
                print(f"Received message: {message}")
                # Pass incoming message to the listener
                await comm_manager.listen_websocket_message(websocket, message)
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            comm_manager.remove_websocket_client(websocket)
    return websocket_handler


async def start_websocket_server(comm_manager):
    """Start WebSocket server on 0.0.0.0:8765

    If the `websockets` package is missing, print setup instructions and
    wait indefinitely so the main program does not crash with ImportError.
    """
    if websockets is None:
        print("websockets package niet geïnstalleerd. Volg deze stappen:")
        print("1) Maak een virtuele omgeving: python3 -m venv .venv")
        print("2) Activeer deze: source .venv/bin/activate")
        print("3) Installeer dependencies: pip install websockets pyserial")
        print("4) Start het spel opnieuw: python3 main.py")
        # keep the coroutine alive so main() doesn't exit immediately
        await asyncio.Future()

    handler = create_websocket_handler(comm_manager)
    print("Starting WebSocket server on 0.0.0.0:8765...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket server is running")
        await asyncio.Future()  # Run forever