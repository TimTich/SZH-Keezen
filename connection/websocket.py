import asyncio

import websockets

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
    """Start WebSocket server on 0.0.0.0:8765"""
    handler = create_websocket_handler(comm_manager)
    print("Starting WebSocket server on 0.0.0.0:8765...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket server is running")
        await asyncio.Future()  # Run forever