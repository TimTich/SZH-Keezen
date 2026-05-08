from flask import Flask, request, jsonify
import serial
import time
import sys
import os

# --- DE ULTIEME ZOEKMACHINE VOOR JE BESTANDEN ---
# Dit stukje zorgt dat Python in AL je submappen zoekt naar player.py, deck.py, etc.
huidige_map = os.path.dirname(os.path.abspath(__file__))
hoofd_map = os.path.abspath(os.path.join(huidige_map, '..'))

if hoofd_map not in sys.path:
    sys.path.append(hoofd_map)

# Zoek ook in alle submappen van SZH-Keezen (zoals 'Logica' of 'Game')
for root, dirs, files in os.walk(hoofd_map):
    if root not in sys.path:
        sys.path.append(root)

# --- EIGEN GAME LOGICA IMPORTEREN ---
try:
    from player import Player
    from deck import Deck
    print("✅ Spel-logica succesvol gevonden en geladen!")
except ImportError as e:
    print(f"❌ FOUT: Kan spel-logica niet vinden! {e}")
    print(f"Ik heb gezocht in: {sys.path[-3:]}") # Laat de laatste 3 plekken zien
    sys.exit(1) # Stop de server als het niet lukt

app = Flask(__name__)

# --- 1. SPEL INITIALISEREN ---
print("--- Keezen Spel opstarten ---")
spelers = []
speel_deck = None

# --- 2. HARDWARE INSTELLINGEN ---
class KeezenHardware:
    def __init__(self):
        self.poort_bord = '/dev/ttyACM0'     
        self.poort_display = '/dev/ttyACM1'  
        
        try:
            self.bord = serial.Serial(self.poort_bord, 115200, timeout=2)
            print("✅ Speelbord verbonden!")
        except Exception:
            self.bord = None
            print("❌ Speelbord NIET gevonden (Simulatiemodus)")

        try:
            self.display = serial.Serial(self.poort_display, 115200, timeout=2)
            print("✅ Display verbonden!")
        except Exception:
            self.display = None
            print("❌ Display NIET gevonden (Simulatiemodus)")
            
        time.sleep(2) 

    def vraag_aantal_spelers(self):
        if not self.display:
            print("SIMULATIE: Geen display gevonden, we gaan uit van 4 spelers.")
            return 4
            
        self.display.write("P:?\n".encode('utf-8'))
        
        start_tijd = time.time()
        while time.time() - start_tijd < 2.0:
            if self.display.in_waiting > 0:
                antwoord = self.display.readline().decode('utf-8').strip()
                if antwoord in ["2", "4"]:
                    print(f" -> Hardware check succesvol: {antwoord} spelers aangesloten.")
                    return int(antwoord)
                    
        print(" -> Geen (of ongeldig) antwoord van display Arduino. Fallback: 4 spelers.")
        return 4

    def stuur_commando(self, doelwit, commando_string):
        bericht = f"{commando_string}\n".encode('utf-8')
        if doelwit == "BORD" and self.bord:
            self.bord.write(bericht)
            return self._wacht_op_antwoord(self.bord, doelwit)
        elif doelwit == "DISPLAY" and self.display:
            self.display.write(bericht)
            return self._wacht_op_antwoord(self.display, doelwit)
        else:
            print(f"TESTMODUS [{doelwit}]: {commando_string}")
            return True

    def _wacht_op_antwoord(self, verbinding, naam):
        start_tijd = time.time()
        while time.time() - start_tijd < 2.0:
            if verbinding.in_waiting > 0:
                antwoord = verbinding.readline().decode('utf-8').strip()
                if antwoord == "OK":
                    return True
        return False

hardware = KeezenHardware()

# --- 3. HARDWARE ROUTES ---
@app.route('/api/status', methods=['GET'])
def check_status():
    return jsonify({"server": "online", "bord_verbonden": hardware.bord is not None, "display_verbonden": hardware.display is not None})

@app.route('/api/bord/led', methods=['POST'])
def stuur_bord():
    data = request.json
    actie_code = "1" if data.get('actie') == "aan" else "0"
    usb_commando = f"L:{data.get('led_id')}:{actie_code}"
    hardware.stuur_commando("BORD", usb_commando)
    return jsonify({"status": "succes"})

@app.route('/api/display/kaart', methods=['POST'])
def stuur_display():
    data = request.json
    usb_commando = f"S:{data.get('slot')}:{data.get('waarde')}"
    hardware.stuur_commando("DISPLAY", usb_commando)
    return jsonify({"status": "succes"})

# --- 4. GAME LOGICA ROUTES ---
@app.route('/api/game/start', methods=['POST'])
def start_game():
    global spelers, speel_deck
    aantal = hardware.vraag_aantal_spelers()
    spelers = []
    for i in range(1, aantal + 1):
        spelers.append(Player(f"Speler {i}", i))
    speel_deck = Deck(spelers)
    speel_deck.dealCards(5)
    return jsonify({"status": "succes", "bericht": f"Nieuw spel gestart met {aantal} spelers."})

@app.route('/api/game/speler/<int:speler_id>', methods=['GET'])
def get_speler_hand(speler_id):
    for p in spelers:
        if p.id == speler_id:
            hand_lijst = [kaart.face for kaart in p.cards]
            return jsonify({"speler_naam": p.name, "hand": hand_lijst})
    return jsonify({"fout": "Speler niet gevonden"}), 404

if __name__ == '__main__':
    print("Keezen Server draait! Wacht op commando's van de Tobii app...")
    app.run(host='0.0.0.0', port=8080)