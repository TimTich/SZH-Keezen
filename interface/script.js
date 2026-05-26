// ============================================
// COMMUNICATIE MET DE RASPBERRY PI
// ============================================
// Let op: als je de interface straks op een los tablet opent, 
// verander 'localhost' dan naar het IP-adres van je Raspberry Pi!
const piAddress = "ws://192.168.1.50:8765";
let socket;
// Vraagt bij het openen van de pagina welk speler-nummer je bent
let invoer = prompt("Welke speler ben je? (Vul in: 0, 1, 2 of 3)", "0");
let spelerId = parseInt(invoer);

function verbindMetPi() {
    socket = new WebSocket(piAddress);

    socket.onopen = function(e) {
        console.log("Verbonden met de Raspberry Pi!");
        // We melden ons direct aan bij de Pi
        verstuurBericht({
            type: "PLAYER_JOIN",
            player_id: spelerId
        });
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log("Bericht van Pi:", data);

        // De Pi bepaalt wat wij op het scherm moeten doen
        if (data.type === "GAME_START") {
            document.getElementById('start-scherm').classList.add('verborgen');
            document.getElementById('spel-scherm').classList.remove('verborgen');
        } 
        else if (data.type === "NIEUWE_HAND") {
            tekenKaarten(data.kaarten); // Tekent de 4 of 5 nieuwe kaarten
        }
        else if (data.type === "UPDATE_BORD") {
            updatePionPosities(data.pionnen); // Past de cijfertjes op de pionnen aan
        }
        else if (data.type === "FOUT_ZET") {
            alert(data.bericht); // Laat de waarschuwing van de Pi zien
            // Haal de groene randjes weg zodat de speler opnieuw kan kiezen
            document.querySelectorAll('.speelkaart-wrapper.geselecteerd').forEach(w => w.classList.remove('geselecteerd'));
            document.querySelectorAll('.pion.geselecteerd').forEach(p => p.classList.remove('geselecteerd'));
            checkSelecties();
        }
    };

    socket.onclose = function(event) {
        console.log("Verbinding met Pi verbroken.");
    };
}

function verstuurBericht(berichtObject) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(berichtObject));
    }
}

// Start de verbinding direct als je de webpagina opent
verbindMetPi();


// ============================================
// UI LOGICA (VISUELE KANT & KLIKKEN)
// ============================================

function startSpel() {
    // Vertel de Pi dat deze speler er klaar voor is
    verstuurBericht({ type: "CONFIRM_START" });
}

function tekenKaarten(hand) {
    const handContainer = document.getElementById('hand-kaarten');
    handContainer.innerHTML = '';
    
    hand.forEach(waarde => {
        const wrapper = document.createElement('div');
        wrapper.className = 'speelkaart-wrapper';
        
        if (waarde === 'gespeeld') {
            const img = document.createElement('img');
            img.src = 'kaart15.png'; // Achterkant
            wrapper.appendChild(img);
            wrapper.classList.add('gespeeld');
            wrapper.style.cursor = 'default';
        } else {
            const img = document.createElement('img');
            // Vertaling van de Pi ('A', 'K') naar jouw plaatjes ('kaart14.png')
            let bestandNaam = waarde;
            if(waarde === 'J') bestandNaam = '11';
            if(waarde === 'Q') bestandNaam = '12';
            if(waarde === 'K') bestandNaam = '13';
            if(waarde === 'A') bestandNaam = '14';
            
            img.src = `kaart${bestandNaam}.png`;
            img.className = 'speelkaart-img';
            img.alt = waarde; 
            wrapper.appendChild(img);
            
            wrapper.onclick = function() { 
                if (!this.classList.contains('gespeeld')) selecteerKaart(this); 
            };
        }
        handContainer.appendChild(wrapper);
    });
}

function updatePionPosities(pionnenData) {
    // De Pi stuurt dit: { "pion-1": "bank", "pion-2": 5, ... }
    for (let pionId in pionnenData) {
        let pionElement = document.querySelector(`.pion[data-id='${pionId}']`);
        if (pionElement) {
            let label = pionElement.querySelector('.pos-label');
            if(label) label.innerText = pionnenData[pionId];
        }
    }
}

function selecteerKaart(el) {
    document.querySelectorAll('.speelkaart-wrapper').forEach(w => w.classList.remove('geselecteerd'));
    el.classList.add('geselecteerd');
    
    const imgEl = el.querySelector('img');
    const kaartNaam = imgEl ? imgEl.alt : "";
    
    if (kaartNaam !== '7') {
        document.querySelectorAll('.pion').forEach(p => p.classList.remove('geselecteerd'));
    }
    updateInstructie();
    checkSelecties(); 
}

function selecteerPion(el) {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    const kaartNaam = geselecteerdeKaart ? geselecteerdeKaart.alt : "";
    
    if (kaartNaam === '7') {
        if (el.classList.contains('geselecteerd')) el.classList.remove('geselecteerd');
        else if (document.querySelectorAll('.pion.geselecteerd').length < 2) el.classList.add('geselecteerd');
    } else {
        document.querySelectorAll('.pion').forEach(p => p.classList.remove('geselecteerd'));
        el.classList.add('geselecteerd');
    }
    checkSelecties(); 
}

function updateInstructie() {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    const instructie = document.getElementById('instructie-tekst');
    instructie.innerText = (geselecteerdeKaart && geselecteerdeKaart.alt === '7') ? "SELECTEER 2 PIONNEN" : "MAAK JE KEUZE";
}

function checkSelecties() {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    const kaartNaam = geselecteerdeKaart ? geselecteerdeKaart.alt : "";
    const aantalPionnen = document.querySelectorAll('.pion.geselecteerd').length;
    const bevestigKnop = document.getElementById('bevestig-knop');

    if (kaartNaam === '7') {
        (aantalPionnen === 2) ? bevestigKnop.classList.remove('uitgeschakeld') : bevestigKnop.classList.add('uitgeschakeld');
    } else {
        (geselecteerdeKaart && aantalPionnen === 1) ? bevestigKnop.classList.remove('uitgeschakeld') : bevestigKnop.classList.add('uitgeschakeld');
    }
}

// ============================================
// ZETTEN DOORSTUREN NAAR DE PI
// ============================================

function speelZet() {
    const kaartElement = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    if (!kaartElement) return;

    const geselecteerdeKaart = kaartElement.alt; // Bijv. "A", "7", of "4"

    if (geselecteerdeKaart === '7') {
        open7Popup();
    } else if (geselecteerdeKaart === 'J') {
        openBoerPopup();
    } else {
        // We spelen een normale kaart
        const pion = document.querySelector('.pion.geselecteerd');
        const pionIdNummer = parseInt(pion.dataset.id.replace('pion-', '')) - 1; // Maakt er 0, 1, 2 of 3 van voor de Pi
        
        // Stuur de zet naar de Pi!
        verstuurBericht({
            type: "CARD_PLAYED",
            player_id: spelerId,
            card: { face: geselecteerdeKaart },
            pion_id: pionIdNummer
        });
        
        draaiGeselecteerdeKaartOm();
    }
}

function bevestig7Zet() { 
    const pionnen = document.querySelectorAll('.pion.geselecteerd');
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img').alt;

    if(pionnen.length === 2) {
        const pion1Id = parseInt(pionnen[0].dataset.id.replace('pion-', '')) - 1;
        const pion2Id = parseInt(pionnen[1].dataset.id.replace('pion-', '')) - 1;

        verstuurBericht({
            type: "CARD_PLAYED",
            player_id: spelerId,
            card: { face: geselecteerdeKaart },
            pion_id: pion1Id,
            pion2_id: pion2Id,
            movePawn2: stappenPionOnder // De Pi berekent pion 1 zelf met (7 - stappenOnder)
        });

        document.getElementById('popup-7').classList.add('verborgen'); 
        draaiGeselecteerdeKaartOm(); 
    }
}

function bevestigBoerZet() { 
    const eigenPion = document.querySelector('.pion.geselecteerd');
    const vijandigePion = document.querySelector('.boer-wrapper.geselecteerd-boer'); 
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img').alt;

    if (eigenPion && vijandigePion) {
        const pionId = parseInt(eigenPion.dataset.id.replace('pion-', '')) - 1;
        
        verstuurBericht({
            type: "CARD_PLAYED",
            player_id: spelerId,
            card: { face: geselecteerdeKaart },
            pion_id: pionId,
            pion2_id: "TBD_VIJAND_ID" // Dit maken we later actief in de Pi
        });

        document.getElementById('popup-boer').classList.add('verborgen'); 
        draaiGeselecteerdeKaartOm(); 
    }
}

function draaiGeselecteerdeKaartOm() {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd');
    if (geselecteerdeKaart) {
        geselecteerdeKaart.querySelector('img').src = 'kaart15.png';
        geselecteerdeKaart.classList.add('gespeeld');
        geselecteerdeKaart.classList.remove('geselecteerd');
        document.querySelectorAll('.pion').forEach(p => p.classList.remove('geselecteerd'));
        
        updateInstructie();
        checkSelecties();
    }
}

// ============================================
// POP-UP LOGICA (Verdeel-schermpjes)
// ============================================

let stappenPionBoven = 0; 
let stappenPionOnder = 0;

function open7Popup() {
    document.getElementById('popup-7').classList.remove('verborgen');
    document.querySelector('#popup-7 .popup-speel-knop').classList.add('uitgeschakeld'); 
    stappenPionBoven = 0;
    stappenPionOnder = 0;
    teken7Stappen();
}

function teken7Stappen() {
    const vakBoven = document.getElementById('stappen-boven');
    const vakOnder = document.getElementById('stappen-onder');
    vakBoven.innerHTML = ''; 
    vakOnder.innerHTML = '';
    
    const svgPion = (isZwart) => `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" class="stap-icoon" width="65" height="95" style="pointer-events: all;">
            <rect width="24" height="36" fill="transparent" />
            <path d="M12,2 C14.2,2 16,3.8 16,6 C16,7.6 15,9 13.6,9.7 C14.5,12 17,19 18,24 L6,24 C7,19 9.5,12 10.4,9.7 C9,9 8,7.6 8,6 C8,3.8 9.8,2 12,2 Z M4,28 L20,28 L20,32 L4,32 L4,28 Z" fill="${isZwart ? 'black' : 'transparent'}" stroke="black" stroke-width="2"/>
        </svg>`;
    
    for (let i = 1; i <= 7; i++) {
        const sB = document.createElement('div'); 
        sB.className = 'stap-wrapper';
        sB.innerHTML = svgPion(i <= stappenPionBoven);
        sB.onclick = () => { 
            stappenPionBoven = i; 
            stappenPionOnder = 7 - i; 
            document.querySelector('#popup-7 .popup-speel-knop').classList.remove('uitgeschakeld'); 
            teken7Stappen(); 
        };
        vakBoven.appendChild(sB);
        
        const sO = document.createElement('div'); 
        sO.className = 'stap-wrapper';
        sO.innerHTML = svgPion(i <= stappenPionOnder);
        sO.onclick = () => { 
            stappenPionOnder = i; 
            stappenPionBoven = 7 - i; 
            document.querySelector('#popup-7 .popup-speel-knop').classList.remove('uitgeschakeld'); 
            teken7Stappen(); 
        };
        vakOnder.appendChild(sO);
    }
}

function openBoerPopup() {
    document.getElementById('popup-boer').classList.remove('verborgen');
    document.getElementById('boer-speel-knop').classList.add('uitgeschakeld');
    tekenBoerPionnen();
}

function tekenBoerPionnen() {
    const kleuren = ['#0066ff', '#cc0000', '#33cc33']; 
    const rijen = ['blauw', 'rood', 'groen'];
    
    rijen.forEach((k, idx) => {
        const rD = document.getElementById(`boer-rij-${k}`);
        rD.innerHTML = ''; 
        for(let i = 0; i < 4; i++) {
            const w = document.createElement('div');
            w.className = 'boer-wrapper'; 
            w.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" class="boer-pion-icoon" width="85" height="120">
                    <rect width="24" height="36" fill="transparent" pointer-events="all"/>
                    <path d="M12,2 C14.2,2 16,3.8 16,6 C16,7.6 15,9 13.6,9.7 C14.5,12 17,19 18,24 L6,24 C7,19 9.5,12 10.4,9.7 C9,9 8,7.6 8,6 C8,3.8 9.8,2 12,2 Z M4,28 L20,28 L20,32 L4,32 L4,28 Z" fill="${kleuren[idx]}" stroke="black" stroke-width="2"/>
                </svg>`;
            w.onclick = function() { selecteerBoerPion(this); };
            rD.appendChild(w);
        }
    });
}

function selecteerBoerPion(el) {
    document.querySelectorAll('.boer-wrapper').forEach(p => p.classList.remove('geselecteerd-boer'));
    el.classList.add('geselecteerd-boer');
    document.getElementById('boer-speel-knop').classList.remove('uitgeschakeld');
}

function stopSpel() {
    document.getElementById('spel-scherm').classList.add('verborgen');
    document.getElementById('start-scherm').classList.remove('verborgen');
}

function openUitlegKeezen() {
    document.getElementById('uitleg-keezen-scherm').classList.remove('verborgen');
}

function sluitUitlegKeezen() {
    document.getElementById('uitleg-keezen-scherm').classList.add('verborgen');
}

function openUitlegUI() {
    document.getElementById('uitleg-ui-scherm').classList.remove('verborgen');
}

function sluitUitlegUI() {
    document.getElementById('uitleg-ui-scherm').classList.add('verborgen');
}