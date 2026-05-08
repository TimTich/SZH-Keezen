import requests
import time

SERVER_URL = "http://127.0.0.1:8080"

print("\n--- 1. SPEL STARTEN ---")
res = requests.post(f"{SERVER_URL}/api/game/start")
print("Antwoord:", res.json())

time.sleep(1)

print("\n--- 2. KAARTEN BEKIJKEN VAN SPELER 1 ---")
res = requests.get(f"{SERVER_URL}/api/game/speler/1")
speler_data = res.json()
print("Antwoord:", speler_data)

time.sleep(1)

print("\n--- 3. HARDWARE KOPPELEN AAN DE SPEL LOGICA ---")
hand = speler_data.get("hand", [])
if len(hand) > 0:
    eerste_kaart = hand[0]
    print(f"Speler 1 heeft als eerste kaart een '{eerste_kaart}'.")
    print(f"We sturen nu een commando om deze kaart te laten zien op flapperdisplay slot 1!")
    
    data_display = {"slot": 1, "waarde": eerste_kaart}
    res = requests.post(f"{SERVER_URL}/api/display/kaart", json=data_display)
    print("Hardware antwoord:", res.json())