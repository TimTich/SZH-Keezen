from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

# --- Game state ---
game_state = {
    "current_player": 1,
    "players": [1, 2, 3, 4]
}

clients: List[WebSocket] = []

def check_swap(player_id):
    return "true"

def calculate_moves(player_id):
    # YOUR RULE LOGIC HERE
    moves = check_pawns(player_id)
    return [
        {"pawn": "one ", "move": moves[0]},
        {"pawn": "two ", "move": moves[1]},
        {"pawn": "three ", "move": moves[2]},
        {"pawn": "four ", "move": moves[3]},

    ]

async def broadcast_state():
    state = {
        "type": "state_update",
        "current_player": game_state["current_player"],
        "possible_moves": calculate_moves(game_state["current_player"]),
        "swap_possible": check_swap(game_state["current_player"])
    }

    for client in clients:
        await client.send_json(state)

@app.websocket("/play_turn")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)

    # Send initial state
    await websocket.send_json({
        "type": "state",
        "data": game_state
    })

    try:
        while True:
            data = await websocket.receive_json()

            # Handle player actions
            if data["type"] == "play_turn":
                player_id = data["player_id"]

                if player_id != game_state["current_player"]:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Not your turn"
                    })
                    continue

                # --- Process move here ---
                if(not process_move()):
                   await websocket.send_json({
                        "type": "wrong_move",
                        "message": "You were not able to play this combination."
                    })
                   continue

                # Advance turn
                next_index = (
                    game_state["players"].index(player_id) + 1
                ) % len(game_state["players"])

                game_state["current_player"] = game_state["players"][next_index]

                # Broadcast updated state
                await broadcast_state()

    except WebSocketDisconnect:
        clients.remove(websocket)