from flask import Flask, request, jsonify
import serial
import time

app = Flask(__name__)

# --- 1. HARDWARE INSTELLINGEN ---
class KeezenHardware:
    def __init__(self):
        print("Hardware initialiseren...")
        # Vervang dit later door de juiste poorten, bijv. /dev/ttyACM0
        self.poort_bord = 'COM3'     # Voorbeeld poort
        self.poort_display = 'COM4'  # Voorbeeld poort
        
        try:
            self.bord = serial.Serial(self.poort_bord, 115200, timeout=1)
            self.display = serial.Serial(self.poort_display, 115200, timeout=1)
            time.sleep(2) # Wacht op Arduino reset
            print("Verbonden met beide Arduino's!")
        except Exception as e:
            print(f"Let op: Start in test-modus (geen Arduino's gevonden). Fout: {e}")
            self.bord = None
            self.display = None

    def stuur_commando(self, doelwit, commando_string):
        """Stuurt de tekst naar de Arduino en wacht heel even"""
        bericht = f"{commando_string}\n".encode('utf-8')
        
        if doelwit == "BORD" and self.bord:
            self.bord.write(bericht)
            print(f"-> USB verzonden naar BORD: {commando_string}")
        elif doelwit == "DISPLAY" and self.display:
            self.display.write(bericht)
            print(f"-> USB verzonden naar DISPLAY: {commando_string}")
        else:
            # Als er geen Arduino is aangesloten, printen we het in de console (handig voor testen!)
            print(f"TESTMODUS [{doelwit}]: {commando_string}")

# Start de hardware koppeling
hardware = KeezenHardware()

# --- 2. WI-FI ONTVANGERS (API ROUTES) ---

@app.route('/api/bord/led', methods=['POST'])
def stuur_bord():
    """
    De Windows App stuurt bijv: {"led_id": 45, "actie": "aan"}
    """
    data = request.json
    led_id = data.get('led_id')
    actie = data.get('actie') # 'aan' of 'uit'
    
    # Vertaal voor de Arduino, bijvoorbeeld: "L:45:1" (Led 45 aan)
    status_code = "1" if actie == "aan" else "0"
    usb_commando = f"L:{led_id}:{status_code}"
    
    hardware.stuur_commando("BORD", usb_commando)
    return jsonify({"status": "succes", "commando": usb_commando})


@app.route('/api/display/kaart', methods=['POST'])
def stuur_display():
    """
    De Windows App stuurt bijv: {"slot": 3, "waarde": "A"} 
    (Slot 1 t/m 5, Waarde 2 t/m 10, J, Q, K, A)
    """
    data = request.json
    slot = data.get('slot')
    waarde = data.get('waarde')
    
    # Controleer of het een geldig slot is (1 t/m 5)
    if slot < 1 or slot > 5:
        return jsonify({"fout": "Ongeldig slot. Kies 1 t/m 5"}), 400
        
    # Vertaal voor de Arduino, bijvoorbeeld: "S:3:A" (Slot 3, Aas)
    usb_commando = f"S:{slot}:{waarde}"
    
    hardware.stuur_commando("DISPLAY", usb_commando)
    return jsonify({"status": "succes", "commando": usb_commando})

# --- 3. SERVER STARTEN ---
if __name__ == '__main__':
    # Start de server op poort 5000, bereikbaar voor alles op de Wi-Fi
    print("Keezen Server draait! Wacht op commando's van de Tobii app...")
    app.run(host='0.0.0.0', port=8080)