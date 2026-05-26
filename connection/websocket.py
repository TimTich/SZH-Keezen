import asyncio

import websockets

async def websocket_handler(websocket, comm_manager, path):
    comm_manager.add_websocket_client(websocket)
    try:
        async for message in websocket:
        # Pass incoming message to the listener
            await comm_manager.listen_websocket_message(websocket, message)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        comm_manager.remove_websocket_client(websocket)

async def start_websocket_server():
    """Start WebSocket server on localhost:8765"""
    async with websockets.serve(websocket_handler, "localhost", 8765):
        await asyncio.Future()  # Run forever