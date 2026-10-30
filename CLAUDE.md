# CLAUDE.md — Vigilo (proiect FIS)

Contextul pentru orice sesiune Claude Code în repo. Citește-l complet înainte de orice modificare.

## 1. Ce construim

**Vigilo**: o cameră căreia îi spui în cuvinte ce să urmărească și ce să facă.

- Utilizatorul scrie ce caută ("person", "cup", "bottle", "backpack").
- Desenează zone pe imaginea camerei și le dă nume ("masa 1", "masa 2").
- Pune reguli: "dacă pe masa 1 rămân obiecte fără nicio persoană peste N secunde, alertă: masă de debarasat".
- Detecția e open-vocabulary: orice obiect scris ca text, fără antrenare.
- Client țintă: cafenele (mese libere, mese nedebarasate, coadă la bar). Al doilea client: magazine mici (raft gol, coadă la casă).

Proiect de echipă la Fundamentele Ingineriei Software (FIS), FMI UniBuc. Nota se dă pe inginerie software: cerințe, arhitectură, design patterns, teste, CI, ADR-uri. Computer vision-ul îl luăm gata făcut; efortul merge în motorul de reguli, produs și calitatea codului.

Vigilo extinde ce descrie deja README-ul ("Real-Time Object Detection & Perimeter Analytics Platform"): zonele sunt geofencing-ul pe care ADR-001 îl lasă pentru mai târziu.

**Termen: demo funcțional luni, 2 noiembrie 2026.**

## 2. Starea repo-ului la pornire (commit `ffde16b`)

| Ce | Stare |
| --- | --- |
| `backend/app/*.py`, `backend/tests/*.py` | **Toate goale (0 bytes).** Backend-ul se scrie de la zero. |
| `backend/Dockerfile` | `python:3.10-slim`, libgl, torch CPU, `requirements.txt`, uvicorn pe 8000 cu `--reload` |
| `backend/requirements.txt` | fastapi 0.115.0, uvicorn 0.30.6, ultralytics 8.3.0, opencv-headless, numpy 1.26.4, pydantic 2.9.2, websockets, lapx, pytest, httpx |
| `frontend/` | React 18 + Vite 5, fără biblioteci de UI. Funcționează azi pentru detecție simplă (vezi mai jos). |
| `frontend/vite.config.js` | Proxy: `/api` și `/ws` merg la backend. **Toate rutele backend stau sub `/api` sau `/ws`.** |
| `docker-compose.yml` | `backend` (8000, volum `./backend:/app`, `DATABASE_PATH=/app/events.sqlite3`) și `frontend` (5173) |
| `.github/workflows/ci.yml` | pytest pe backend (Python 3.10, instalează torch CPU + requirements) și `npm run build` pe frontend. Rulează pe `main` și `feature/**`. |
| `docs/ADR-001-...md` | Frame-uri JPEG binare pe `/ws/detect`; răspuns JSON + JPEG adnotat; fiecare detecție salvată în SQLite; geofencing amânat. |
| `README.md` | Instrucțiuni Windows, Docker Desktop, model `yolo11n.pt`. |

Ce face frontend-ul azi:
- `VisionViewport.jsx`: `getUserMedia`, desenează cadrul pe un canvas ascuns, îl trimite ca JPEG binar pe `/ws/detect` la fiecare 100 ms. Primește `{"type":"telemetry","detections":[...]}` sau `{"type":"error","message":...}` ca text și un JPEG adnotat ca binar, pe care îl afișează ca `<img>`. Elementul `<video>` e ascuns.
- `App.jsx`: butoane start/stop, citește `/api/events?limit=20` la fiecare 3 s.
- `EventLog.jsx`: afișează `event.label`, `event.confidence`, `event.created_at` (o detecție pe rând).
- `TelemetryBar.jsx`: starea conexiunii și numărul de obiecte din ultimul cadru.

## 3. Decizii noi față de ADR-001 (de scris ca ADR-002 la pasul 1)

1. **Desenarea se face în browser, nu pe server.** Serverul nu mai trimite JPEG adnotat, doar JSON. Browserul afișează `<video>` live (fluid, 30 FPS) și un `<canvas>` suprapus pe care desenează box-urile, zonele și starea lor. Motive: video fluid chiar dacă detecția merge la 5 FPS, jumătate din trafic, iar desenarea zonelor cu mouse-ul are nevoie oricum de un canvas peste video.
2. **Zonele și regulile intră acum** (geofencing-ul amânat în ADR-001). Coordonatele sunt normalizate 0..1 față de cadru, deci nu e nevoie de coordonate de cameră.
3. **Nu mai salvăm fiecare detecție.** La 5 FPS ar însemna mii de rânduri pe minut fără nicio valoare. Salvăm doar evenimente: schimbări de stare a zonelor și reguli declanșate sau închise. `EventLog` se adaptează.
4. **Detector open-vocabulary** (YOLO-World) cu fallback pe `yolo11n.pt`.

Ce rămâne din ADR-001: frame-uri JPEG binare de la client la server pe `/ws/detect`.

## 4. Scope

### Obligatoriu pentru demo-ul de luni

1. Webcam în browser → JPEG binar pe `/ws/detect` → backend → JSON înapoi.
2. Detector open-vocabulary cu vocabular setabil din interfață; fallback pe `yolo11n.pt`.
3. Box-uri desenate pe un canvas suprapus peste `<video>`.
4. Zone poligonale desenate cu mouse-ul peste video, cu nume.
5. Motorul de reguli cu 3 tipuri: `presence`, `left_unattended`, `count_threshold`.
6. Starea fiecărei zone (FREE / OCCUPIED / NEEDS_CLEARING), colorată pe video și afișată în panou.
7. Evenimente în `EventLog`, salvate în SQLite.
8. FPS și latența de inferență în `TelemetryBar`.
9. Sursă alternativă: fișier video încărcat din browser (planul B pentru demo).
10. Teste pentru reguli, zone, API, WebSocket și privacy, verzi în CI.
11. `docker compose up --build` pornește tot.

### NU pentru luni (backlog, nu începe fără să fie cerut)

- Broker MQTT (ținta arhitecturii finale; până atunci, `EventBus` în proces cu aceeași interfață).
- Raspberry Pi / Jetson, imagini multi-arch (`docker buildx`).
- Tracking cu ID-uri (ByteTrack), blurarea fețelor, regula `zone_empty`, notificări pe telefon, statistici pe oră, embeddings pentru un obiect anume, autentificare.

## 5. De ce camera e în browser

Docker Desktop pe Windows nu dă containerului acces la un webcam USB. Browserul ia camera cu `getUserMedia` și trimite cadrele; backend-ul nu atinge hardware-ul. Merge identic pe orice laptop din echipă și cu telefonul, deschizând interfața în browserul lui. Webcam-ul în browser cere `localhost` sau HTTPS.

## 6. Arhitectura

```
Browser (React)                          Backend (FastAPI, Python 3.10)
---------------                          ------------------------------
<video> live (webcam sau fișier)
  -> canvas ascuns -> JPEG  == WS binar ==> /ws/detect
                                              -> Detector (Strategy: openvocab | yolo | fake)
                                              -> zones.assign (ce detecții cad în ce zonă)
                                              -> RuleEngine (stări + timere pe zonă)
                                              -> EventBus (Observer)
                                                   -> EventRepository (SQLite)
                                                   -> WS JSON înapoi
<canvas> suprapus: box-uri, zone, stări <== WS JSON ==
```

Module în `backend/app/`:

| Modul | Rol | Pattern |
| --- | --- | --- |
| `main.py` | `create_app(detector=None, db_path=None, clock=None)` + `app = create_app()`; rute REST, WebSocket, wiring | Factory |
| `schemas.py` | Modelele Pydantic (secțiunea 7) | — |
| `detector.py` | Interfața `Detector` + `OpenVocabDetector` + `YoloDetector` + `FakeDetector` | Strategy |
| `zones.py` | Point-in-polygon (ray casting scris de noi, fără shapely), maparea detecțiilor pe zone | — |
| `rules.py` | `RuleEngine`: mașina de stări pe zonă, timere, debounce | State |
| `events.py` | `EventBus` cu `subscribe`/`publish`; mâine MQTT cu aceeași interfață | Observer |
| `database.py` | SQLite (modulul standard `sqlite3`): zone, reguli, vocabular, evenimente | Repository |
| `clock.py` | `Clock` injectabil: `SystemClock` și `FakeClock` pentru teste | — |

Reguli de arhitectură:

- **`RuleEngine` nu importă nimic legat de cameră, OpenCV sau Ultralytics.** Primește `list[Detection]` și un timestamp. Se testează fără model.
- **Timpul vine din `Clock` injectat**, niciodată `time.time()` direct în reguli.
- **`create_app` primește dependențele.** Testele dau `FakeDetector`, o bază temporară și `FakeClock`. Nimic nu încarcă un model la import.
- **Importurile Ultralytics sunt leneșe**, în interiorul `OpenVocabDetector` și `YoloDetector`, ca testele să pornească repede.
- **Backpressure:** clientul trimite următorul cadru doar după ce primește răspunsul la cel curent, la cel mult 10 FPS. Serverul procesează un cadru o dată.
- **Inferența rulează în thread separat** (`asyncio.to_thread` sau `run_in_threadpool`), ca să nu blocheze bucla async.
- **Coordonate normalizate 0..1** peste tot în contract.
- O detecție aparține unei zone dacă **centrul de jos al box-ului** e în poligon.

## 7. Modele de date (Pydantic v2, compatibile cu Python 3.10)

```python
class Detection(BaseModel):
    label: str
    confidence: float                        # 0..1
    box: tuple[float, float, float, float]   # x1, y1, x2, y2 normalizate 0..1

class ZoneIn(BaseModel):
    name: str
    polygon: list[tuple[float, float]]       # >= 3 puncte, normalizate 0..1

class Zone(ZoneIn):
    id: str

class RuleIn(BaseModel):
    zone_id: str
    type: Literal["presence", "left_unattended", "count_threshold"]
    target_labels: list[str]                 # ex. ["cup", "bottle"] sau ["person"]
    seconds: float = 0
    threshold: int | None = None             # doar pentru count_threshold
    enabled: bool = True

class Rule(RuleIn):
    id: str

class Event(BaseModel):
    id: int
    created_at: datetime                     # UTC
    zone_id: str
    zone_name: str
    rule_id: str | None
    kind: Literal["zone_state_changed", "rule_triggered", "rule_cleared"]
    detail: dict
```

Validări: poligon cu cel puțin 3 puncte și coordonate în [0, 1]; `threshold` obligatoriu la `count_threshold`; `seconds >= 0`; `zone_id` existent.

## 8. Logica regulilor

Fiecare zonă are o stare:

```
FREE --(persoană prezentă >= 1 s)--> OCCUPIED
OCCUPIED --(nicio persoană >= T, obiecte țintă prezente)--> NEEDS_CLEARING
OCCUPIED --(nicio persoană >= T, fără obiecte țintă)--> FREE
NEEDS_CLEARING --(fără obiecte țintă >= 2 s)--> FREE
NEEDS_CLEARING --(persoană prezentă >= 1 s)--> OCCUPIED
```

`T` și obiectele țintă vin din regula `left_unattended` a zonei. Fără o astfel de regulă, zona trece doar între FREE și OCCUPIED.

- `presence`: adevărată cât timp cel puțin un `target_label` e în zonă de cel puțin `seconds`.
- `left_unattended`: un `target_label` e în zonă și nicio `person` nu e în zonă, de cel puțin `seconds`. Asta produce NEEDS_CLEARING.
- `count_threshold`: numărul de detecții cu `target_labels` din zonă > `threshold`, continuu, de cel puțin `seconds`.

**Debounce obligatoriu:** o condiție se consideră întreruptă doar dacă lipsește continuu cel puțin 0.5 s. Detectorul pierde obiecte pentru un cadru sau două; fără debounce, demo-ul pâlpâie.

Fiecare regulă emite `rule_triggered` o singură dată la intrarea în condiție și `rule_cleared` la ieșire. Fiecare schimbare de stare emite un `zone_state_changed` cu `{"from": ..., "to": ...}`. Niciodată un eveniment pe cadru.

Etichetele se compară normalizat: litere mici, fără spații la capete.

## 9. Detectorul

Interfață:

```python
class Detector(Protocol):
    name: str
    def set_vocabulary(self, words: list[str]) -> list[str]: ...  # întoarce cuvintele nesuportate
    def detect(self, jpeg: bytes) -> list[Detection]: ...
```

- **`OpenVocabDetector`** (implicit): `ultralytics.YOLOWorld("yolov8s-worldv2.pt")` și `model.set_classes(words)`. Verificat în codul Ultralytics 8.3.0: `set_classes` importă pachetul `clip` și, dacă lipsește, încearcă să-l instaleze din git la runtime, apoi descarcă modelul CLIP ViT-B/32. Ca să nu se întâmple asta la runtime:
  - adaugă `git` la pachetele `apt-get` din `backend/Dockerfile`;
  - adaugă `clip @ git+https://github.com/ultralytics/CLIP.git` în `requirements.txt`;
  - cheamă `set_classes` la pornire și la fiecare schimbare de vocabular, protejat de un `threading.Lock` (nu în timpul unei inferențe).
  - `set_vocabulary` întoarce listă goală (orice cuvânt e suportat).
- **`YoloDetector`** (fallback): `ultralytics.YOLO("yolo11n.pt")`, clase COCO. Filtrează rezultatele la vocabular; `set_vocabulary` întoarce cuvintele care nu sunt clase COCO.
- **`FakeDetector`** (teste): întoarce detecții programate dinainte, fără model.
- Selecție prin variabila de mediu `VIGILO_DETECTOR=openvocab|yolo` (implicit `openvocab`). Dacă `openvocab` nu se poate încărca, loghează motivul și treci pe `yolo`. `/api/health` arată detectorul activ.
- Decodare JPEG cu `cv2.imdecode`. `imgsz=640`, prag de încredere `VIGILO_CONF` (implicit 0.25). CPU implicit, fără CUDA.
- Măsoară timpul de inferență per cadru și trimite-l în telemetrie.
- Greutățile și cache-ul CLIP se descarcă la prima pornire. În `docker-compose.yml` adaugă un volum numit pentru `/root/.cache`, ca să nu se descarce la fiecare rebuild.
- **Testele nu descarcă modele.** Doar testele marcate `@pytest.mark.model` încarcă un model real, iar CI le sare (`pytest -m "not model"`). Înregistrează marker-ul în `backend/pytest.ini`.

## 10. Contractul API (stabil: frontend și backend se lucrează în paralel)

REST, totul sub `/api`:

| Metodă | Rută | Ce face |
| --- | --- | --- |
| GET | `/api/health` | `{"status":"ok","detector":"openvocab","unsupported":[...]}` |
| GET / PUT | `/api/vocabulary` | `{"words": [...]}`; PUT întoarce și `unsupported` |
| GET / POST | `/api/zones` | listă / creare (`ZoneIn` → `Zone`) |
| DELETE | `/api/zones/{id}` | șterge zona și regulile ei |
| GET / POST | `/api/rules` | listă / creare (`RuleIn` → `Rule`) |
| PATCH / DELETE | `/api/rules/{id}` | modificare parțială / ștergere |
| GET | `/api/events?limit=50` | ultimele evenimente, cele mai noi primele |

WebSocket `/ws/detect`:

- client → server: mesaje **binare**, fiecare un JPEG.
- server → client, text JSON, un mesaj per cadru procesat:

```json
{
  "type": "telemetry",
  "frame_id": 42,
  "infer_ms": 87.5,
  "detector": "openvocab",
  "detections": [{"label": "cup", "confidence": 0.81, "box": [0.41, 0.52, 0.48, 0.63]}],
  "zones": [{"id": "z1", "name": "masa 1", "state": "NEEDS_CLEARING", "counts": {"cup": 1}}],
  "events": [{"id": 7, "kind": "rule_triggered", "zone_name": "masa 1", "...": "..."}]
}
```

- la eroare: `{"type": "error", "message": "..."}` și conexiunea rămâne deschisă (un JPEG stricat nu închide sesiunea).

## 11. Frontend

Păstrează stilul existent (obiecte `styles` inline, tema întunecată, fără biblioteci noi).

- `VisionViewport.jsx`: `<video>` vizibil + `<canvas>` suprapus, aceeași dimensiune afișată. Desenează box-urile din ultima telemetrie și zonele colorate după stare (FREE verde, OCCUPIED albastru, NEEDS_CLEARING portocaliu), cu numele zonei. Trimite cadrul următor doar după răspuns. Sursa: webcam sau fișier video (`<input type="file" accept="video/*">`, redat în buclă).
- Mod "desenează zonă": click-uri pe canvas adaugă puncte, dublu-click închide poligonul, apoi cere numele și face `POST /api/zones`. Coordonatele se normalizează la dimensiunea video-ului, nu a elementului afișat (atenție la `object-fit`).
- `ControlPanel.jsx`: start/stop, alegerea sursei, câmp de vocabular (cuvinte separate prin virgulă, `PUT /api/vocabulary`, afișează cuvintele nesuportate), lista zonelor cu starea și butonul de ștergere, formular de regulă (zonă, tip, etichete, secunde, prag).
- `EventLog.jsx`: evenimentele noi din `/api/events`, cu ora, zona, tipul și detaliul.
- `TelemetryBar.jsx`: conexiune, detector activ, FPS efectiv, `infer_ms`, număr de obiecte.

## 12. Privacy (cerințe nefuncționale, testate)

- Niciun cadru nu se scrie pe disc. `test_privacy.py` rulează un ciclu complet pe WebSocket cu `FakeDetector` într-un director temporar și verifică că apare doar fișierul SQLite.
- SQLite conține doar zone, reguli, vocabular și evenimente: text și numere, fără imagini.
- Fără recunoaștere facială și fără identificarea persoanelor. `person` e doar o clasă.
- Serverul nu retransmite imagini.

## 13. Teste

- `tests/test_zones.py`: punct înăuntru, în afară, pe margine, poligon concav, coordonate la limita cadrului.
- `tests/test_rules.py`: fiecare tranziție din secțiunea 8 cu `FakeClock`, debounce-ul de 0.5 s, emiterea unică a evenimentelor, cele 3 tipuri de reguli, reguli dezactivate.
- `tests/test_api.py`: rutele REST și validările (poligon invalid, `count_threshold` fără prag, zonă inexistentă).
- `tests/test_ws.py`: `/ws/detect` cu `FakeDetector` și `TestClient.websocket_connect`: trimite JPEG-uri, primește telemetrie, primește `error` la un JPEG stricat fără să se închidă conexiunea, iar evenimentele ajung în `/api/events`.
- `tests/test_privacy.py`: testul din secțiunea 12.
- Un test `@pytest.mark.model` care încarcă detectorul real și rulează pe o imagine generată.
- Nu declara o sarcină terminată fără să rulezi testele și să arăți output-ul real.

## 14. Comenzi

Docker:

```powershell
docker compose up --build
```

Interfața: <http://localhost:5173>. Backend: <http://localhost:8000/api/health>.

Backend local (PowerShell, Windows):

```powershell
cd backend
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pytest -m "not model" -v
python -m uvicorn app.main:app --reload
```

Dacă PowerShell blochează activarea: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

Frontend local:

```powershell
cd frontend
npm install
npm run dev
```

## 15. Ordinea de lucru până luni

Lucrul se face pe branch-ul `feature/vigilo` (CI rulează pe `feature/**`). Fiecare pas se termină cu testele verzi și un commit.

1. `docs/ADR-002-zones-rules-client-overlay.md` (secțiunea 3) + `schemas.py`, `clock.py`, `zones.py`, `pytest.ini` + `test_zones.py`.
2. `rules.py` + `test_rules.py` complet. E inima proiectului.
3. `events.py` + `database.py`.
4. `detector.py` cu `FakeDetector`, `YoloDetector`, `OpenVocabDetector`; modificările din `requirements.txt`, `Dockerfile`, `docker-compose.yml` și CI (`-m "not model"`).
5. `main.py` (`create_app`, REST, WebSocket) + `test_api.py`, `test_ws.py`, `test_privacy.py`.
6. Frontend (secțiunea 11).
7. README actualizat (Vigilo, comenzi, FPS măsurat pe calculatorul de dezvoltare); `docker compose up --build` pornește tot.
8. Repetiția scenariului de demo (secțiunea 16) de 3 ori la rând fără eroare.

## 16. Scenariul de demo

1. Două zone pe catedră: "masa 1", "masa 2". Vocabular: person, cup, bottle. Regulă `left_unattended` pe fiecare masă, `seconds = 20`, ținte cup și bottle.
2. Un coleg stă la masa 1 cu o cană → OCCUPIED.
3. Pleacă și lasă cana → după 20 s → NEEDS_CLEARING, alertă în log.
4. Profesorul alege un obiect de pe birou; îl adăugăm în vocabular și e detectat pe loc.
5. Comutăm pe fișier video; totul merge la fel.

Obiecte de mărimea unei căni sau mai mari; obiectele mici se detectează prost de la distanță.

## 17. Convenții

- Python 3.10 (ca în Dockerfile și CI), type hints peste tot, Pydantic v2.
- Fără dependențe noi în afară de `clip` (secțiunea 9) fără să spui de ce.
- React funcțional cu hooks, fără biblioteci de UI.
- Fără emoji nicăieri: cod, UI, commit-uri, documente.
- Commit-uri mici, la imperativ: `rules: add left_unattended debounce`.
- La finalul fiecărui pas arată diff-ul real (`git diff --stat` + diff-ul fișierelor importante) și output-ul real al testelor, nu un rezumat.
- Orice acțiune pe care doar omul o poate face (instalări cu drepturi de admin, setări GitHub, permisiuni de cameră, push dacă nu ai acces) merge într-o listă separată, cu titlul "De făcut de tine", la final.
- Orice decizie nouă de arhitectură primește un ADR scurt în `docs/` (context, decizie, alternative, consecințe).
- Dacă ceva din fișierul ăsta contrazice codul existent, oprește-te și întreabă.