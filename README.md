# Real-Time Object Detection & Perimeter Analytics Platform

Modular computer-vision dashboard built with React, FastAPI, Ultralytics
YOLO11n, binary WebSockets, and SQLite.

## Requirements

- Windows 10/11 with Docker Desktop and Docker Compose, or Python 3.10 and
  Node.js 20 for running the services locally.
- A camera connected to the computer. The browser will ask for camera access.

## Run with Docker Desktop (recommended on Windows)

Open PowerShell in the project directory and run:

```powershell
docker compose up --build
```

Open <http://localhost:5173>. Allow camera access, then select **Start
detection**. The backend is available at <http://localhost:8000/api/health>.
Press `Ctrl+C` in PowerShell to stop the services.

The first detection may take longer because Ultralytics downloads the
`yolo11n.pt` model. Camera frames are sent as binary JPEG WebSocket messages;
detections are saved to the SQLite database at `backend/events.sqlite3`.

## Run without Docker

Use two PowerShell windows.

Backend:

```powershell
cd backend
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. If PowerShell blocks virtual environment
activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
in that backend window and activate again.

## Tests and build

From the project root:

```powershell
cd backend
python -m pytest -v
cd ..\frontend
npm install
npm run build
```

## Repository structure

- `backend/app/`: API, SQLite persistence, schemas, and YOLO detector.
- `backend/tests/`: API and binary WebSocket tests using a test detector.
- `frontend/src/`: React dashboard and camera stream components.
- `.github/workflows/ci.yml`: backend tests and frontend production build.
- `docs/`: architecture decision records.
