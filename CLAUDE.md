# CLAUDE.md — Vigilo (proiect FIS)

Contextul pentru orice sesiune Claude Code în repo. Citește-l complet înainte de orice modificare. Înlocuiește complet versiunea veche (detecție de obiecte pentru cafenele), care nu mai e valabilă.

## 1. Produsul

**Vigilo: când alarma tace, camera nu doarme.**

Magazinele mici au alarme care uneori nu funcționează: pică, sunt dezactivate sau sunt tăiate. Vigilo se conectează la camerele pe care magazinul le are deja și urmărește noaptea comportamentul din jurul ușii și din interior. Când vede ceva suspect, trimite proprietarului pe telefon o alertă cu o poză. **Proprietarul decide** dacă sună la 112. Sistemul nu cheamă niciodată singur poliția.

Ce înseamnă „suspect” (semnale, nu identitate):
- o persoană stă prea mult în zona roșie din fața ușii sau a geamului (loitering);
- un grup de persoane stă în zona roșie;
- intrări repetate în zona roșie într-un interval scurt (cineva se tot întoarce la ușă);
- orice persoană în interior cât timp sistemul e armat (intruziune);
- camera nu mai trimite imagine cât timp sistemul e armat (curent sau internet tăiat).

Client principal: proprietarul unui magazin mic (1–5 locații), care nu e în magazin noaptea și are deja camere (de obicei un DVR Hikvision sau Dahua cu RTSP). Mall-urile și dispeceratele de pază sunt extindere, nu scope.

Diferența față de detecția de intruziune din camerele Hikvision/Dahua: comportament în timp (nu un singur eveniment), alarme false puține și reglabile, escaladare dacă proprietarul nu răspunde, alertă „cameră offline”, merge cu orice cameră RTSP, română și Telegram.

Proiect de echipă la Fundamentele Ingineriei Software (FIS), FMI UniBuc. Nota se dă pe inginerie software: cerințe, arhitectură, design patterns, teste, CI, ADR-uri. Detecția de persoane o luăm gata făcută (YOLO); efortul merge în motorul de comportament, fluxul de alertă și calitatea codului.

## 2. Ce NU facem (decizii luate, nu reveni asupra lor fără echipă)

- **Fără recunoaștere facială și fără identificarea persoanelor.** Datele faciale sunt date biometrice (GDPR art. 9); camerele unui magazin filmează angajați și trecători. Tehnic nu merge oricum iarna (glugă, fular). Pentru a nu primi alerte când vine proprietarul: armare pe program + buton „Sunt eu / Dezarmează” în aplicație și în notificare.
- **Fără detecție de „om mascat” ca semnal de alarmă.** Iarna dă alarme false constant.
- **Fără apel automat la 112.** Omul decide.
- **Fără detecție de furt în timpul programului, arme, obiecte.** Alt produs.
- **Fără Raspberry Pi / hardware dedicat.** Rulează pe un PC sau laptop din magazin, ori pe orice server.
- **Fără YOLO-World / open-vocabulary.** Pentru persoane ajunge `yolo11n.pt` (clasa `person`), mai rapid și fără dependența CLIP.

## 3. Starea repo-ului la pornire

**`main` (commit `6e3a26b`), ce au făcut colegii:**

| Ce | Stare |
| --- | --- |
| `frontend/` | React 18 + Vite + Tailwind (dark) + Konva + Zustand. Arată bine; **se păstrează**. |
| `frontend/src/api.js` | `USE_MOCK = true`: nu vorbește cu backend-ul. Rute așteptate: `POST/DELETE /api/zones`, `POST/DELETE /api/rules`. |
| `frontend/src/components/VisionViewport.jsx` | `<img src="http://localhost:8000/api/video_feed">` (MJPEG de la backend) cu fallback pe o poză Unsplash. Desenează **dreptunghiuri** în pixeli pe un `Stage` Konva 640x480. Zona are `tip: 'normala' \| 'interzisa'`. |
| `frontend/src/components/EventLog.jsx` | **Generează alerte aleatorii** (simulare). Trebuie înlocuit cu evenimente reale. |
| `frontend/src/store.js`, `soundAlert.js`, `StatsDropdown.jsx` | Store Zustand, sunet la alertă critică, contoare. |
| UI | Conține emoji (în opțiuni și etichete). Trebuie scoase (vezi convenții). |
| `backend/app/` | 106 linii: FastAPI + SQLAlchemy cu 3 rute fără prefix `/api`. `sqlalchemy` **nu** e în `requirements.txt`, deci backend-ul nu pornește. `detector.py` gol. |
| `backend/tests/` | Gol. **De aceea CI-ul pică**: pytest iese cu cod 5 când nu găsește niciun test. |
| `docs/ADR-001`, `docs/ADR-002-frontend-state-canvas.md` | ADR-002 = Konva + Zustand în frontend. Următorul ADR e **ADR-003**. |

**Branch-ul `feature/vigilo` (Darius): motorul care se refolosește.** Backend complet, 139 de teste, scris pentru varianta veche (cafenea). Se portează pe `main`, nu se face merge orb:

| Modul pe `feature/vigilo` | Ce se refolosește |
| --- | --- |
| `app/zones.py` | point-in-polygon (ray casting), maparea detecțiilor pe zone: **direct** |
| `app/clock.py` | `SystemClock` / `FakeClock`: **direct** |
| `app/events.py` | `EventBus` (Observer): **direct** |
| `app/database.py` | repository pe `sqlite3` standard: **se adaptează** la noile tabele (secțiunea 7) și înlocuiește SQLAlchemy |
| `app/rules.py` | debounce-ul, timerele, emiterea unică a evenimentelor: **se adaptează** la regulile de securitate (secțiunea 8); mașina de stări de cafenea (FREE/OCCUPIED/NEEDS_CLEARING) dispare |
| `app/detector.py` | `YoloDetector` + `FakeDetector`: **se adaptează** (tracking, doar `person`); `OpenVocabDetector` dispare |
| `app/main.py` | `create_app(...)` cu dependențe injectate: **pattern-ul se păstrează** |
| `tests/` | stilul de teste (FakeClock, FakeDetector, bază temporară): **se păstrează** |

Comandă pentru a vedea un fișier de pe branch fără să schimbi branch-ul: `git show feature/vigilo:backend/app/rules.py`.

## 4. Scope pentru demo

1. Sursă video pe server: cameră RTSP, fișier video sau webcam local. Configurabilă din API.
2. Detecție `person` cu `yolo11n.pt` + tracking ByteTrack (ID per persoană).
3. Flux MJPEG pe `/api/video_feed`, 640x480, cu box-urile persoanelor desenate de server.
4. Zone dreptunghiulare desenate în frontend (`normala` / `interzisa`), salvate în backend.
5. Armare: program zilnic (ex. 22:00–07:00, ora României) + armare/dezarmare manuală.
6. Reguli de securitate (secțiunea 8): `loiter`, `group`, `repeated_entries`, `intrusion`, `camera_offline`.
7. Incidente cu poză (doar la alarmă), severitate, stare: deschis / confirmat / alarmă falsă / escaladat.
8. Notificare pe Telegram cu poza și butoane: „Mă ocup”, „Alarmă falsă”, „Ignoră 1 oră”.
9. Escaladare: dacă incidentul nu e confirmat în N minute, alerta pleacă la a doua persoană.
10. Frontend legat de backend: zone, reguli, armare, incidente cu poză și butoane.
11. Teste verzi în CI și un script de evaluare pe clipuri etichetate (secțiunea 12).
12. `docker compose up --build` pornește tot.

Backlog (nu începe fără să fie cerut): MQTT, mai multe camere simultan, aplicație mobilă proprie, WhatsApp, integrare cu VMS-uri de mall, dezarmare pe baza telefonului acasă.

## 5. Arhitectura

```
Cameră RTSP / fișier / webcam
        |
   VideoSource (Strategy: RtspSource | FileSource | DeviceSource), thread separat
        |  cadre
   PersonTracker (yolo11n + ByteTrack) -----> MJPEG /api/video_feed (box-uri + ID)
        |  list[Track]
   zones.assign  ->  SecurityEngine (reguli + armare + debounce, Clock injectat)
        |  RuleHit
   IncidentManager (agregare, cooldown, poză, escaladare)
        |  Incident
   EventBus (Observer)
     |-> IncidentRepository (SQLite) + SnapshotStore (fișiere JPEG, retenție)
     |-> Notifier (Strategy: TelegramNotifier | FakeNotifier)
     |-> WebSocket /ws/events -> frontend
```

Module în `backend/app/`:

| Modul | Rol | Pattern |
| --- | --- | --- |
| `main.py` | `create_app(source=None, tracker=None, db_path=None, clock=None, notifier=None)`, rute, WebSocket, pornirea pipeline-ului | Factory |
| `schemas.py` | modele Pydantic (secțiunea 7) | — |
| `video.py` | `VideoSource` + `RtspSource`, `FileSource`, `DeviceSource`, `FakeSource`; reconectare automată | Strategy |
| `tracker.py` | `PersonTracker` (Ultralytics `model.track(..., persist=True, tracker="bytetrack.yaml", classes=[0])`) + `FakeTracker` | Strategy |
| `zones.py` | geometrie, mapare track → zone (centrul de jos al box-ului) | — |
| `schedule.py` | armarea: program + override manual, fus orar `Europe/Bucharest` | — |
| `security.py` | `SecurityEngine`: regulile din secțiunea 8 | State |
| `incidents.py` | `IncidentManager`: agregare, cooldown, escaladare, stări | State |
| `snapshots.py` | salvare JPEG la incident, ștergere după retenție | — |
| `notify.py` | `Notifier` + `TelegramNotifier` (prin `httpx`) + `FakeNotifier` | Strategy |
| `events.py` | `EventBus` | Observer |
| `database.py` | repository-uri `sqlite3`: zone, reguli, setări, incidente | Repository |
| `clock.py` | `Clock` injectabil | — |

Reguli de arhitectură:
- `SecurityEngine` și `IncidentManager` nu importă OpenCV, Ultralytics sau `httpx`. Primesc `list[Track]` și timestamp. Se testează fără model și fără rețea.
- Timpul vine doar din `Clock` injectat.
- Importurile Ultralytics sunt leneșe (în `PersonTracker`), ca testele să pornească repede.
- Pipeline-ul video rulează într-un thread de fundal; API-ul nu se blochează pe inferență.
- Coordonatele zonelor sunt normalizate 0..1 în backend. Frontend-ul convertește din pixelii stage-ului 640x480.
- Cadrul MJPEG e exact 640x480 (letterbox dacă sursa are alt raport), ca dreptunghiurile din Konva să cadă exact pe imagine. Schimbă `object-cover` în `object-contain` în `VisionViewport.jsx`.
- Notificările nu blochează pipeline-ul (coadă + thread sau `asyncio` task).

## 6. De ce sursa video e pe server acum

Camerele de magazin sunt camere IP / DVR cu RTSP; browserul nu poate deschide RTSP. Serverul se conectează la cameră, rulează detecția și trimite fluxul MJPEG către frontend (exact ce așteaptă deja `VisionViewport.jsx`). Docker Desktop pe Windows nu vede webcam-uri USB, dar vede camere din rețea fără probleme. Pentru dezvoltare fără cameră IP: fișier video sau telefonul ca cameră RTSP (aplicații de tip „IP Webcam”).

## 7. Modele de date și contractul API

```python
class ZoneIn(BaseModel):
    name: str
    kind: Literal["normal", "forbidden"]
    rect: tuple[float, float, float, float]     # x, y, w, h normalizate 0..1

class RuleIn(BaseModel):
    zone_id: str
    type: Literal["loiter", "group", "repeated_entries", "intrusion"]
    seconds: float = 0          # loiter, group, intrusion
    min_people: int | None = None   # group
    entries: int | None = None      # repeated_entries
    window_seconds: float | None = None  # repeated_entries
    severity: Literal["low", "high"] = "high"
    enabled: bool = True

class Incident(BaseModel):
    id: int
    opened_at: datetime            # UTC
    zone_id: str | None            # None pentru camera_offline
    zone_name: str | None
    rule_types: list[str]          # toate regulile agregate în incident
    severity: Literal["low", "high"]
    status: Literal["open", "acknowledged", "false_alarm", "escalated", "closed"]
    people_count: int
    snapshot_url: str | None       # /api/incidents/{id}/snapshot
```

REST, totul sub `/api`:

| Metodă | Rută | Ce face |
| --- | --- | --- |
| GET | `/api/health` | status, sursa video, detector, FPS, armat sau nu |
| GET / PUT | `/api/source` | `{"kind": "rtsp" \| "file" \| "device", "uri": "..."}` |
| GET | `/api/video_feed` | MJPEG `multipart/x-mixed-replace`, 640x480 |
| GET / POST, DELETE | `/api/zones`, `/api/zones/{id}` | zone |
| GET / POST, PATCH / DELETE | `/api/rules`, `/api/rules/{id}` | reguli |
| GET / PUT | `/api/arming` | `{"mode": "schedule" \| "armed" \| "disarmed", "schedule": {"start": "22:00", "end": "07:00"}, "armed_now": true}` |
| GET | `/api/incidents?limit=50` | cele mai noi primele |
| GET | `/api/incidents/{id}/snapshot` | JPEG-ul incidentului |
| POST | `/api/incidents/{id}/ack`, `/false_alarm`, `/snooze` | acțiunile din notificare și din UI |

WebSocket `/ws/events`: server → client, JSON `{"type": "incident", "incident": {...}}` și `{"type": "status", "fps": ..., "armed_now": ..., "people": ...}`.

`api.js` se schimbă pe `USE_MOCK = false` și pe aceste rute; frontend-ul convertește `coordonate {x, y, width, height}` (pixeli 640x480) în `rect` normalizat și invers. `tip: 'interzisa'` ↔ `kind: 'forbidden'`.

## 8. Regulile de securitate

Se evaluează **doar cât timp sistemul e armat** (excepție: `camera_offline` se verifică și el doar când e armat).

- `loiter`: același track ID stă în zona `forbidden` continuu cel puțin `seconds` (implicit 60; demo 15).
- `group`: cel puțin `min_people` track-uri distincte simultan în zonă, cel puțin `seconds` (implicit 3 persoane, 10 s).
- `repeated_entries`: cel puțin `entries` intrări în zonă în `window_seconds` (implicit 3 în 600 s). **Numără intrările, nu ID-urile**: ByteTrack dă ID nou cine iese din cadru și revine.
- `intrusion`: orice persoană în zonă cel puțin `seconds` (implicit 2). Gândit pentru zonele din interior.
- `camera_offline`: niciun cadru primit de cel puțin 30 s cât timp e armat. Incident `high` fără zonă, fără poză (sau ultima poză disponibilă).

Comportament comun:
- **Debounce 1 s**: o persoană pierdută de detector 1–2 cadre nu resetează timerul.
- **Agregare**: regulile declanșate în aceeași zonă cât un incident e deschis se adaugă la el (`rule_types`), nu fac incident nou. Severitatea crește la `high` dacă oricare regulă e `high`.
- **Cooldown**: după închiderea unui incident, aceeași zonă nu mai deschide altul timp de 5 minute (configurabil).
- **Ignoră 1 oră** (`snooze`): zona nu deschide incidente o oră.
- **Escaladare**: incident `open` neconfirmat după 3 minute (configurabil) → `escalated`, notificare la contactul secundar.
- Fiecare tranziție emite un eveniment pe `EventBus`, niciodată un eveniment pe cadru.

## 9. Notificări (Telegram)

- Bot creat de om din @BotFather. Config din variabile de mediu, citite dintr-un fișier `.env` care **nu intră în git**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (proprietar), `TELEGRAM_ESCALATION_CHAT_ID` (al doilea contact). Fără token → `ConsoleNotifier` care doar loghează; aplicația pornește oricum.
- `sendPhoto` cu poza incidentului, text în română (zona, ce s-a întâmplat, câte persoane, ora locală) și `inline_keyboard` cu „Mă ocup” / „Alarmă falsă” / „Ignoră 1 oră”.
- Răspunsurile la butoane: `getUpdates` cu long polling într-un thread (nu avem URL public pentru webhook), apoi `answerCallbackQuery` și acțiunea pe incident.
- Text exemplu: „Vigilo: 2 persoane stau de 3 minute la ușa magazinului (zona Intrare), 02:14. Tu decizi dacă suni la 112.”
- `httpx` e deja în `requirements.txt`; nu adăuga altă bibliotecă de Telegram.

## 10. Privacy și legal (cerințe nefuncționale, testate)

- Nicio identificare de persoane; `person` e doar o clasă, ID-ul de tracking e temporar și nu se salvează.
- Cadre pe disc **doar** ca poză de incident, în `SNAPSHOT_DIR`, șterse automat după `SNAPSHOT_RETENTION_DAYS` (implicit 7).
- Fără înregistrare video continuă.
- În SQLite: zone, reguli, setări, incidente (text și numere, calea pozei).
- Documentația de business menționează: afiș „Zonă supravegheată video”, camerele acoperă spațiul propriu al magazinului, evaluare de impact (DPIA) înainte de folosire reală.
- `test_privacy.py`: rulează pipeline-ul cu `FakeSource` + `FakeTracker` fără incidente → în director apare doar baza SQLite; cu un incident → apare exact o poză; după retenție → poza dispare.

## 11. Teste

- `test_zones.py`: geometrie (se portează de pe `feature/vigilo`).
- `test_schedule.py`: program care trece de miezul nopții (22:00–07:00), exact la limite, override manual, fus orar.
- `test_security.py`: fiecare regulă cu `FakeClock`; debounce; `repeated_entries` cu ID-uri diferite; nimic când e dezarmat; `camera_offline`.
- `test_incidents.py`: agregare, cooldown, snooze, escaladare, tranzițiile de stare.
- `test_notify.py`: `FakeNotifier` primește exact o notificare per incident; `TelegramNotifier` cu `httpx.MockTransport` (fără rețea) trimite `sendPhoto` cu butoanele corecte și tratează callback-urile.
- `test_api.py`, `test_ws.py`: rute, validări, WebSocket cu dependențe false.
- `test_privacy.py`: secțiunea 10.
- Testele care încarcă modelul real: `@pytest.mark.model`, sărite în CI (`pytest -m "not model"`); marker înregistrat în `backend/pytest.ini`.
- Nu declara o sarcină terminată fără să rulezi testele și să arăți output-ul real.

## 12. Evaluarea (metrica principală pentru FIS)

Produsul trăiește sau moare prin alarmele false. În `eval/`:
- 10–20 de clipuri scurte filmate de echipă la o ușă (trecători normali, cineva care așteaptă, un grup, cineva care se tot întoarce, intrare în interior), cu un fișier `labels.csv`: clip, ce incident ar trebui să apară (sau niciunul).
- `eval/run_eval.py` rulează pipeline-ul pe clipuri (cu `FileSource` și modelul real) și scrie precizia (câte alerte sunt reale) și recall-ul (câte situații reale au fost prinse), plus FPS-ul.
- Clipurile video nu intră în git (doar `labels.csv` și scriptul); se țin local sau pe Drive.

## 13. Comenzi

Docker (orice OS): `docker compose up --build`. Interfață: <http://localhost:5173>. Backend: <http://localhost:8000/api/health>.

Backend local, Linux/macOS:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pytest -m "not model" -v
python -m uvicorn app.main:app --reload
```

Windows (PowerShell): la fel, cu `py -3.10 -m venv .venv` și `.\.venv\Scripts\Activate.ps1`.

Frontend: `cd frontend && npm install --legacy-peer-deps && npm run dev` (vezi ADR-002 pentru `--legacy-peer-deps`).

## 14. Ordinea de lucru

Branch nou din `main`: `feature/security-engine`. Fiecare pas: teste verzi, diff real, commit.

1. `docs/ADR-003-security-pivot.md`: pivotul (secțiunile 1, 2, 6), sursa video pe server, poze doar la incident, Telegram, SQLAlchemy înlocuit cu `sqlite3` (motiv: repository-ul testat de pe `feature/vigilo`, o dependență mai puțin). Port `clock.py`, `zones.py`, `events.py`, `pytest.ini` + teste. Șterge backend-ul SQLAlchemy. **CI devine verde aici.**
2. `schedule.py`, `security.py` + teste. Inima proiectului.
3. `incidents.py`, `snapshots.py`, `database.py` + teste.
4. `notify.py` (Fake, Console, Telegram cu MockTransport) + teste.
5. `video.py`, `tracker.py`, pipeline-ul în thread, `/api/video_feed`; modificările din `Dockerfile` (`tzdata` dacă `zoneinfo` nu găsește fusul orar), `docker-compose.yml` (`env_file: .env`, volume pentru cache-ul de modele și pentru `SNAPSHOT_DIR`) și CI (`-m "not model"`).
6. `main.py`: `create_app`, toate rutele, `/ws/events` + `test_api.py`, `test_ws.py`, `test_privacy.py`.
7. Frontend: `USE_MOCK = false`, rutele noi, conversia coordonatelor, `object-contain`, eliminarea generatorului de alerte aleatorii, panou de armare (program + buton), listă de incidente cu poză și butoane, sunet doar pe incident real, fără emoji.
8. `eval/` + README (comenzi, captură, precizie și FPS măsurate) + `docker compose up --build` pe o mașină curată.
9. Repetiția demo-ului (secțiunea 15) de 3 ori la rând fără eroare.

## 15. Scenariul de demo

1. Sursa: telefonul ca cameră RTSP îndreptat spre ușa sălii (sau fișier video de rezervă). Zona roșie „Intrare” desenată în jurul ușii. Armare manuală: „armat”.
2. Un coleg stă la ușă 15 s → alertă Telegram cu poza pe telefonul proprietarului, incident în dashboard, sunet.
3. Apăsăm „Mă ocup” în Telegram → incidentul devine confirmat și în dashboard.
4. Trei colegi stau împreună la ușă → incident `group`.
5. Nu răspundem 3 minute (setat la 30 s pentru demo) → escaladare la al doilea telefon.
6. Oprim fluxul camerei → alertă „cameră offline”.
7. Trecem pe „program”: în afara intervalului nu mai apar alerte.

## 16. Convenții

- Python 3.10, type hints, Pydantic v2.
- Fără dependențe noi fără motiv scris în commit (excepție permisă: `tzdata`).
- React funcțional, Tailwind (deja în proiect), fără alte biblioteci de UI.
- Fără emoji nicăieri: cod, UI, commit-uri, documente, notificări.
- Text pentru utilizator în română; cod și identificatori în engleză.
- Commit-uri mici, la imperativ: `security: add loiter rule with debounce`.
- La finalul fiecărui pas: `git diff --stat`, diff-ul fișierelor importante și output-ul real al testelor, nu un rezumat.
- Acțiunile pe care doar omul le poate face (token Telegram, setări GitHub, URL-ul și parola camerei, instalări cu admin, push dacă nu ai acces) merg într-o listă separată „De făcut de tine”, la final.
- Secretele (token, parola camerei) doar în `.env`, niciodată în cod sau în git. Verifică `.gitignore`.
- Orice decizie nouă de arhitectură primește un ADR scurt în `docs/` (context, decizie, alternative, consecințe).
- Nu se face push direct pe `main` pentru cod: branch + pull request + CI verde.
- Dacă ceva din fișierul ăsta contrazice codul existent, oprește-te și întreabă.
