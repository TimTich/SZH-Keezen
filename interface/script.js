// ============================================
// COMMUNICATIE MET DE RASPBERRY PI
// ============================================
const hostName = window.location.hostname || "localhost";
const piAddress = `ws://${hostName}:8765`;
let socket;
let huidigeSpeler = 0;
let globalePionnenStatus = {}; 
let weggooiOpties = {}; 

let opgeslagenId = sessionStorage.getItem('keezenSpelerId');
let spelerId = opgeslagenId !== null ? parseInt(opgeslagenId) : null;

if (spelerId !== null) {
    updateJouwSpeler(spelerId);
} else {
    const jouwSpelerElement = document.getElementById('jouw-speler');
    if (jouwSpelerElement) jouwSpelerElement.textContent = `Aanmelden...`;
}

function verbindMetPi() {
    socket = new WebSocket(piAddress);

    socket.onopen = function(e) {
        console.log("Verbonden met de Raspberry Pi!");
        verstuurBericht({ type: "PLAYER_JOIN", player_id: spelerId });
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === "GAME_START") {
            document.getElementById('start-scherm').classList.add('verborgen');
            document.getElementById('spel-scherm').classList.remove('verborgen');
        } 
        else if (data.type === "PLAYER_COUNT") {
            updateSpelerTeller(data.player_count);
        }
        else if (data.type === "ASSIGNED_PLAYER_ID") {
            spelerId = data.player_id;
            sessionStorage.setItem('keezenSpelerId', spelerId); 
            updateJouwSpeler(spelerId);
            updateBeurtStatus();
        }
        else if (data.type === "NIEUWE_HAND") {
            if (data.weggooi_opties) weggooiOpties = data.weggooi_opties;
            tekenKaarten(data.kaarten); 
        }
        else if (data.type === "UPDATE_BORD") {
            updatePionPosities(data.pionnen); 
            if(data.alle_pionnen) {
                globalePionnenStatus = data.alle_pionnen;
            }
        }
        else if (data.type === "CURRENT_PLAYER") {
            updateHuidigeBeurt(data.player_id);
        }
        else if (data.type === "MOVE_SUCCEEDED") {
            draaiGeselecteerdeKaartOm();
        }
        else if (data.type === "FLIP_ALL_CARDS") {
            draaiAlleKaartenOm();
        }
        else if (data.type === "FOUT_ZET") {
            alert(data.bericht); 
            document.querySelectorAll('.speelkaart-wrapper.geselecteerd').forEach(w => w.classList.remove('geselecteerd'));
            document.querySelectorAll('.pion.geselecteerd').forEach(p => p.classList.remove('geselecteerd'));
            checkSelecties();
        }
        // NIEUW: De Win Activering!
        else if (data.type === "GAME_WON") {
            document.getElementById('spel-scherm').classList.add('verborgen');
            const winScherm = document.getElementById('win-scherm');
            winScherm.classList.remove('verborgen');
            
            const subTitel = document.getElementById('win-subtitel');
            const hoofdTekst = document.getElementById('win-hoofdtekst');
            
            if (data.player_id === spelerId) {
                hoofdTekst.innerText = "JIJ HEBT GEWONNEN!!!";
                subTitel.innerText = "Gefeliciteerd, wat een prestatie!";
            } else {
                hoofdTekst.innerText = "SPEL AFGELOPEN";
                subTitel.innerText = `Speler ${data.player_id + 1} heeft het spel gewonnen!`;
            }
        }
    };
}

function verstuurBericht(berichtObject) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(berichtObject));
    }
}

function updateSpelerTeller(aantalSpelers) {
    const teller = document.getElementById('speler-teller');
    if (teller) teller.textContent = `${aantalSpelers}/4`;
    
    const speelKnop = document.getElementById('speel-knop');
    if (speelKnop) {
        if (aantalSpelers >= 2 && aantalSpelers <= 4) {
            speelKnop.classList.remove('uitgeschakeld');
        } else {
            speelKnop.classList.add('uitgeschakeld');
        }
    }
}

function updateHuidigeBeurt(playerId) {
    huidigeSpeler = playerId;
    const beurtElement = document.getElementById('huidige-beurt');
    if (beurtElement) beurtElement.textContent = `HUIDIGE BEURT: speler ${playerId + 1}`;
    updateBeurtStatus();
}

function updateBeurtStatus() {
    const bevestigKnop = document.getElementById('bevestig-knop');
    const jouwSpelerGameElement = document.getElementById('jouw-speler-game');
    
    if (bevestigKnop) {
        if (spelerId === huidigeSpeler) bevestigKnop.classList.remove('uitgeschakeld');
        else bevestigKnop.classList.add('uitgeschakeld');
    }
    if (jouwSpelerGameElement) {
        const weergaveId = spelerId + 1;
        jouwSpelerGameElement.textContent = spelerId === huidigeSpeler ? `Jij bent speler ${weergaveId} (jouw beurt)` : `Jij bent speler ${weergaveId}`;
    }
    checkSelecties();
}

function updateJouwSpeler(playerId) {
    const weergaveId = playerId + 1;
    const jouwSpelerElement = document.getElementById('jouw-speler');
    if (jouwSpelerElement) jouwSpelerElement.textContent = `Jij bent speler ${weergaveId}`;
    const jouwSpelerGameElement = document.getElementById('jouw-speler-game');
    if (jouwSpelerGameElement) jouwSpelerGameElement.textContent = `Jij bent speler ${weergaveId}`;
}

verbindMetPi();

// ============================================
// UI LOGICA (VISUELE KANT & KLIKKEN)
// ============================================

window.startSpel = function() {
    const knop = document.getElementById('speel-knop');
    if (knop && knop.classList.contains('uitgeschakeld')) return; 
    verstuurBericht({ type: "CONFIRM_START" });
};

function tekenKaarten(hand) {
    const handContainer = document.getElementById('hand-kaarten');
    handContainer.innerHTML = '';
    
    hand.forEach(waarde => {
        const wrapper = document.createElement('div');
        wrapper.className = 'speelkaart-wrapper';
        
        if (waarde === 'gespeeld') {
            const img = document.createElement('img');
            img.src = 'kaart15.png';
            img.className = 'speelkaart-img'; 
            wrapper.appendChild(img);
            wrapper.classList.add('gespeeld');
            wrapper.style.cursor = 'default';
        } else {
            const img = document.createElement('img');
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
    for (let pionId in pionnenData) {
        let pionElement = document.querySelector(`.pion[data-id='${pionId}']`);
        if (pionElement) {
            let label = pionElement.querySelector('.pos-label');
            if (label) label.innerText = pionnenData[pionId];
        }
    }
}

function selecteerKaart(el) {
    if (spelerId !== huidigeSpeler) {
        alert(`Wacht op jouw beurt. Het is nu de beurt van speler ${huidigeSpeler + 1}.`);
        return;
    }

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
    if (spelerId !== huidigeSpeler) {
        alert(`Wacht op jouw beurt. Het is nu de beurt van speler ${huidigeSpeler + 1}.`);
        return;
    }

    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    const kaartNaam = geselecteerdeKaart ? geselecteerdeKaart.alt : "";
    
    if (kaartNaam === '7') {
        if (el.classList.contains('geselecteerd')) {
            el.classList.remove('geselecteerd');
        } else if (document.querySelectorAll('.pion.geselecteerd').length < 2) {
            el.classList.add('geselecteerd');
        }
    } else {
        document.querySelectorAll('.pion').forEach(p => p.classList.remove('geselecteerd'));
        el.classList.add('geselecteerd');
    }
    
    updateInstructie();
    checkSelecties(); 
}

function updateInstructie() {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    const aantalPionnen = document.querySelectorAll('.pion.geselecteerd').length;
    const instructie = document.getElementById('instructie-tekst');
    
    if(instructie) {
        if (!geselecteerdeKaart) {
            instructie.innerText = "MAAK JE KEUZE";
        } else if (geselecteerdeKaart.alt === '7') {
            if (aantalPionnen === 0) instructie.innerText = "SELECTEER 1 OF 2 PIONNEN OM TE SPELEN";
            else instructie.innerText = "KLIK NU OP SPEEL";
        } else {
            if (aantalPionnen === 0) instructie.innerText = "SELECTEER EEN PION OM TE SPELEN";
            else instructie.innerText = "KLIK NU OP SPEEL";
        }
    }
}

function checkSelecties() {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    const kaartNaam = geselecteerdeKaart ? geselecteerdeKaart.alt : "";
    const aantalPionnen = document.querySelectorAll('.pion.geselecteerd').length;
    
    const bevestigKnop = document.getElementById('bevestig-knop');
    const weggooiKnop = document.getElementById('weggooi-knop');

    let speelActief = false;
    let weggooiActief = false;

    if (spelerId === huidigeSpeler && geselecteerdeKaart) {
        if (kaartNaam === '7') {
            speelActief = (aantalPionnen === 1 || aantalPionnen === 2);
        } else {
            speelActief = (aantalPionnen === 1);
        }
        
        let magWeggooienVanPython = (weggooiOpties[kaartNaam] === true);
        weggooiActief = (aantalPionnen === 0 && magWeggooienVanPython);
    }

    if (bevestigKnop) {
        if (speelActief) {
            bevestigKnop.classList.remove('uitgeschakeld');
            bevestigKnop.style.pointerEvents = 'auto';
            bevestigKnop.style.filter = 'grayscale(0%)';
            bevestigKnop.style.opacity = '1';
        } else {
            bevestigKnop.classList.add('uitgeschakeld');
            bevestigKnop.style.pointerEvents = 'none';
            bevestigKnop.style.filter = 'grayscale(100%)';
            bevestigKnop.style.opacity = '0.5';
        }
    }

    if (weggooiKnop) {
        if (weggooiActief) {
            weggooiKnop.classList.remove('uitgeschakeld');
            weggooiKnop.style.pointerEvents = 'auto';
            weggooiKnop.style.filter = 'grayscale(0%)';
            weggooiKnop.style.opacity = '1';
        } else {
            weggooiKnop.classList.add('uitgeschakeld');
            weggooiKnop.style.pointerEvents = 'none';
            weggooiKnop.style.filter = 'grayscale(100%)';
            weggooiKnop.style.opacity = '0.5';
        }
    }
}

function gooiKaartWeg() {
    if (spelerId !== huidigeSpeler) return;
    
    const kaartElement = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    if (!kaartElement) return;

    const geselecteerdeKaart = kaartElement.alt; 
    
    verstuurBericht({
        type: "DISCARD_CARD",
        player_id: spelerId,
        card: { face: geselecteerdeKaart }
    });
}

function speelZet() {
    if (spelerId !== huidigeSpeler) return;

    const kaartElement = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    if (!kaartElement) return;

    const geselecteerdeKaart = kaartElement.alt; 

    if (geselecteerdeKaart === '7') {
        const pionnen = document.querySelectorAll('.pion.geselecteerd');
        let activePawns = 0;
        document.querySelectorAll('.pion').forEach(p => {
            const lbl = p.querySelector('.pos-label');
            if (lbl && lbl.innerText !== 'B') activePawns++;
        });

        if (activePawns === 0 || pionnen.length === 1) {
            const pionIdNummer = parseInt(pionnen[0].dataset.id.replace('pion-', '')) - 1; 
            verstuurBericht({
                type: "CARD_PLAYED",
                player_id: spelerId,
                card: { face: geselecteerdeKaart },
                pion_id: pionIdNummer
            });
        } else if (pionnen.length === 2) {
            // NIEUW: Pak de labels van de pionnen en stuur ze door naar de 7-popup!
            const lbl1 = pionnen[0].querySelector('.pos-label') ? pionnen[0].querySelector('.pos-label').innerText : "?";
            const lbl2 = pionnen[1].querySelector('.pos-label') ? pionnen[1].querySelector('.pos-label').innerText : "?";
            open7Popup(lbl1, lbl2);
        }

    } else if (geselecteerdeKaart === 'J') {
        let hasValidOwn = false;
        let hasValidEnemy = false;
        
        if (globalePionnenStatus[spelerId]) {
            hasValidOwn = globalePionnenStatus[spelerId].some(p => p.is_valid_own);
        }
        
        for (let targetId in globalePionnenStatus) {
            if (parseInt(targetId) === spelerId) continue;
            if (globalePionnenStatus[targetId].some(p => p.is_valid)) {
                hasValidEnemy = true;
                break;
            }
        }
        
        if (!hasValidOwn || !hasValidEnemy) {
            const pion = document.querySelector('.pion.geselecteerd');
            const pionIdNummer = parseInt(pion.dataset.id.replace('pion-', '')) - 1; 
            verstuurBericht({
                type: "CARD_PLAYED",
                player_id: spelerId,
                card: { face: geselecteerdeKaart },
                pion_id: pionIdNummer
            });
        } else {
            openBoerPopup();
        }
        
    } else {
        const pion = document.querySelector('.pion.geselecteerd');
        const pionIdNummer = parseInt(pion.dataset.id.replace('pion-', '')) - 1; 
        
        verstuurBericht({
            type: "CARD_PLAYED",
            player_id: spelerId,
            card: { face: geselecteerdeKaart },
            pion_id: pionIdNummer
        });
    }
}

function bevestig7Zet() { 
    if (spelerId !== huidigeSpeler) return;
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
            movePawn2: stappenPionOnder
        });
        document.getElementById('popup-7').classList.add('verborgen'); 
    }
}

function draaiGeselecteerdeKaartOm() {
    const geselecteerdeKaart = document.querySelector('.speelkaart-wrapper.geselecteerd');
    if (geselecteerdeKaart) {
        geselecteerdeKaart.querySelector('img').src = 'kaart15.png';
        geselecteerdeKaart.querySelector('img').className = 'speelkaart-img'; 
        geselecteerdeKaart.classList.add('gespeeld');
        geselecteerdeKaart.classList.remove('geselecteerd');
        document.querySelectorAll('.pion').forEach(p => p.classList.remove('geselecteerd'));
        
        updateInstructie();
        checkSelecties();
    }
}

function draaiAlleKaartenOm() {
    document.querySelectorAll('.speelkaart-wrapper').forEach(wrapper => {
        if (!wrapper.classList.contains('gespeeld')) {
            const img = wrapper.querySelector('img');
            if (img) {
                img.src = 'kaart15.png';
                img.className = 'speelkaart-img'; 
            }
            wrapper.classList.add('gespeeld');
            wrapper.classList.remove('geselecteerd');
        }
    });
    document.querySelectorAll('.pion').forEach(p => p.classList.remove('geselecteerd'));
    updateInstructie();
    checkSelecties();
}

/* ============================================
   7 POPUP
   ============================================ */
let stappenPionBoven = 0; 
let stappenPionOnder = 0;

function open7Popup(label1, label2) {
    document.getElementById('popup-7').classList.remove('verborgen');
    document.querySelector('#popup-7 .popup-speel-knop').classList.add('uitgeschakeld'); 
    stappenPionBoven = 0;
    stappenPionOnder = 0;
    
    // Injecteer de labels naast de pionnen
    document.getElementById('label-7-boven').innerText = label1 || "?";
    document.getElementById('label-7-onder').innerText = label2 || "?";
    
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

/* ============================================
   DE BOER (J) DYNAMISCHE POPUP
   ============================================ */
let geselecteerdeBoerPionInfo = null;

function openBoerPopup() {
    document.getElementById('popup-boer').classList.remove('verborgen');
    const speelKnop = document.getElementById('boer-speel-knop');
    
    if(speelKnop) {
        speelKnop.classList.add('uitgeschakeld');
        speelKnop.style.pointerEvents = 'none';
        speelKnop.style.backgroundColor = 'gray';
        speelKnop.style.filter = 'grayscale(100%)';
    }
    
    geselecteerdeBoerPionInfo = null;
    tekenBoerPionnen();
}

function tekenBoerPionnen() {
    const container = document.getElementById('boer-tegenstanders-container');
    if(!container) return;
    container.innerHTML = '';
    
    const kleuren = ['#0066ff', '#cc0000', '#33cc33', '#ff9900']; 
    
    for (let targetId in globalePionnenStatus) {
        if (parseInt(targetId) === spelerId) continue; 
        
        const pionnenLijst = globalePionnenStatus[targetId];
        
        const rijDiv = document.createElement('div');
        rijDiv.className = 'boer-speler-rij';
        
        const titel = document.createElement('h3');
        titel.textContent = `Speler ${parseInt(targetId) + 1}`;
        titel.className = 'boer-speler-titel';
        rijDiv.appendChild(titel);
        
        const pionnenDiv = document.createElement('div');
        pionnenDiv.className = 'boer-pionnen-container';
        
        pionnenLijst.forEach(pionInfo => {
            const w = document.createElement('div');
            w.className = 'boer-wrapper';
            if (!pionInfo.is_valid) {
                w.classList.add('ongeldig');
            }
            
            const kleur = kleuren[parseInt(targetId) % kleuren.length];
            
            w.innerHTML = `
                <div class="boer-label">${pionInfo.label}</div>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" class="boer-pion-icoon" width="60" height="85">
                    <path d="M12,2 C14.2,2 16,3.8 16,6 C16,7.6 15,9 13.6,9.7 C14.5,12 17,19 18,24 L6,24 C7,19 9.5,12 10.4,9.7 C9,9 8,7.6 8,6 C8,3.8 9.8,2 12,2 Z M4,28 L20,28 L20,32 L4,32 L4,28 Z" fill="${pionInfo.is_valid ? kleur : '#888'}" stroke="black" stroke-width="2"/>
                </svg>
            `;
            
            if (pionInfo.is_valid) {
                w.onclick = function() { selecteerBoerPion(this, targetId, pionInfo.id); };
            }
            
            pionnenDiv.appendChild(w);
        });
        
        rijDiv.appendChild(pionnenDiv);
        container.appendChild(rijDiv);
    }
}

function selecteerBoerPion(el, targetId, pionId) {
    document.querySelectorAll('.boer-wrapper').forEach(p => p.classList.remove('geselecteerd-boer'));
    el.classList.add('geselecteerd-boer');
    geselecteerdeBoerPionInfo = { target_player_id: targetId, pion_id: pionId };
    
    const speelKnop = document.getElementById('boer-speel-knop');
    if(speelKnop) {
        speelKnop.classList.remove('uitgeschakeld');
        speelKnop.style.pointerEvents = 'auto';
        speelKnop.style.filter = 'none';
        speelKnop.style.backgroundColor = '#cc0000';
    }
}

function bevestigBoerZet() { 
    if (spelerId !== huidigeSpeler) return;
    const eigenPion = document.querySelector('.pion.geselecteerd');
    const kaartImg = document.querySelector('.speelkaart-wrapper.geselecteerd img');
    if (!kaartImg) return;
    const geselecteerdeKaart = kaartImg.alt;

    if (eigenPion && geselecteerdeBoerPionInfo) {
        const pionId = parseInt(eigenPion.dataset.id.replace('pion-', '')) - 1;
        
        verstuurBericht({
            type: "CARD_PLAYED",
            player_id: spelerId,
            card: { face: geselecteerdeKaart },
            pion_id: pionId,
            pion2_id: geselecteerdeBoerPionInfo.pion_id,
            target_player_id: geselecteerdeBoerPionInfo.target_player_id
        });
        document.getElementById('popup-boer').classList.add('verborgen'); 
    } else {
        alert("Zorg dat je een eigen pion hebt geselecteerd op het bord!");
    }
}

function stopSpel() {
    document.getElementById('spel-scherm').classList.add('verborgen');
    document.getElementById('start-scherm').classList.remove('verborgen');
}

function openUitlegKeezen() { document.getElementById('uitleg-keezen-scherm').classList.remove('verborgen'); }
function sluitUitlegKeezen() { document.getElementById('uitleg-keezen-scherm').classList.add('verborgen'); }
function openUitlegUI() { document.getElementById('uitleg-ui-scherm').classList.remove('verborgen'); }
function sluitUitlegUI() { document.getElementById('uitleg-ui-scherm').classList.add('verborgen'); }

document.addEventListener('DOMContentLoaded', () => {
    const speelKnopStart = document.getElementById('speel-knop');
    if (speelKnopStart) speelKnopStart.addEventListener('click', startSpel);
});