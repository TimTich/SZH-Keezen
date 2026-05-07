from flask import Flask, request, jsonify
import serial
import time

app = Flask(__name__)


class KeezenHardware:
    def __init__(self):
        print("--- Keezen Hardware opstarten ---")
        
        # Dit zijn de standaard poortnamen voor Arduino Uno's op een Raspberry Pi (Linux)
        self.poort_bord = '/dev/ttyACM0'     
        self.poort_display = '/dev/ttyACM1'  
        
        # Probeer verbinding te maken met het Speelbord
        try:
            self.bord = serial.Serial(self.poort_bord, 115200, timeout=2)
            print(f"✅ Speelbord verbonden op {self.poort_bord}")
        except Exception:
            print(f"❌ Speelbord NIET gevonden op {self.poort_bord} (Simulatie-modus aan)")
            self.bord = None

        # Probeer verbinding te maken met het Display
        try:
            self.display = serial.Serial(self.poort_display, 115200, timeout=2)
            print(f"✅ Display verbonden op {self.poort_display}")
        except Exception:
            print(f"❌ Display NIET gevonden op {self.poort_display} (Simulatie-modus aan)")
            self.display = None

        # Wacht even zodat de Arduino's rustig kunnen resetten na het inpluggen
        time.sleep(2) 

    def stuur_commando(self, doelwit, commando_string):
        """Stuurt de tekst naar de Arduino en wacht op een 'OK' terug."""
        bericht = f"{commando_string}\n".encode('utf-8')
        
        if doelwit == "BORD" and self.bord:
            self.bord.write(bericht)
            return self._wacht_op_antwoord(self.bord, doelwit)
            
        elif doelwit == "DISPLAY" and self.display:
            self.display.write(bericht)
            return self._wacht_op_antwoord(self.display, doelwit)
            
        else:
            print(f"TESTMODUS [{doelwit}]: {commando_string}")
            return True # In test-modus doen we alsof het altijd lukt

    def _wacht_op_antwoord(self, verbinding, naam):
        """Wacht maximaal 2 seconden tot de Arduino 'OK' zegt."""
        start_tijd = time.time()
        while time.time() - start_tijd < 2.0:
            if verbinding.in_waiting > 0:
                antwoord = verbinding.readline().decode('utf-8').strip()
                if antwoord == "OK":
                    print(f"  -> {naam} bevestigt: OK")
                    return True
        
        print(f"  ⚠️ LET OP: Timeout! Geen 'OK' ontvangen van {naam}.")
        return False

# Start de hardware koppeling
hardware = KeezenHardware()


# --- API ROUTES VOOR DE TOBII APP ---

@app.route('/api/status', methods=['GET'])
def check_status():
    """Hiermee kan de Windows App checken of de Pi en Arduino's online zijn."""
    return jsonify({
        "server": "online",
        "bord_verbonden": hardware.bord is not None,
        "display_verbonden": hardware.display is not None
    })

@app.route('/api/bord/led', methods=['POST'])
def stuur_bord():
    data = request.json
    led_id = data.get('led_id')
    actie = data.get('actie') 
    
    status_code = "1" if actie == "aan" else "0"
    usb_commando = f"L:{led_id}:{status_code}"
    
    gelukt = hardware.stuur_commando("BORD", usb_commando)
    return jsonify({"status": "succes" if gelukt else "fout", "commando": usb_commando})

@app.route('/api/display/kaart', methods=['POST'])
def stuur_display():
    data = request.json
    slot = data.get('slot')
    waarde = data.get('waarde')
    
    if slot < 1 or slot > 5:
        return jsonify({"fout": "Ongeldig slot"}), 400
        
    usb_commando = f"S:{slot}:{waarde}"
    
    gelukt = hardware.stuur_commando("DISPLAY", usb_commando)
    return jsonify({"status": "succes" if gelukt else "fout", "commando": usb_commando})


if __name__ == '__main__':
    # We gebruiken poort 8080, die werkte perfect op jouw systeem!
    app.run(host='0.0.0.0', port=8080)