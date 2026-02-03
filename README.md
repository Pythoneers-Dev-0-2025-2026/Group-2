# Python Guardian

Desktop security system that uses a webcam to distinguish the device owner from intruders. When an unknown face is detected, the system can lock the workstation (Windows), send alerts to a backend, and optionally notify via Telegram. An Android app can connect to the backend over WebSocket to view live state and send commands (e.g. lock).

---

## Features

- **Face enrollment**: Capture many samples of the owner’s face into `backend/data/enrolled/owner/`.
- **LBPH model training**: Train a local face recognizer from enrolled images (saved under `backend/data/models/`).
- **Live monitoring**: Camera feed with owner vs intruder labels; intruder snapshots saved to `backend/data/intruders/`.
- **Server mode**: Run the monitor and a WebSocket server together; clients receive state (threat, fps, faces, image) and can send commands (e.g. lock).
- **Windows lock**: Optional integration to lock the workstation on intruder detection or remote command.
- **Alerts**: Optional HTTP POST to a configurable backend URL and optional Telegram photo on intruder detection.

---

## Requirements

- Python 3 (tested with 3.x)
- Webcam
- For face recognition: **opencv-contrib-python** (LBPH). If you only have `opencv-python`, install `opencv-contrib-python` and uninstall `opencv-python` if both are present.

---

## Project structure

```
Group-2-lastmindesign/
  backend/                    # Python backend
    camera/
      camera.py               # Frame capture, encode
      enroll.py               # Owner face enrollment
      train_and_monitor.py    # Train LBPH, monitor (owner vs intruder)
      screenshots/            # Optional Telegram / image helpers
    server.py                 # WebSocket server + camera monitor
    services.py               # Windows lock, lock-status check
    requirements.txt
    data/                     # Created at runtime (do not commit)
      enrolled/owner/         # Enrollment images
      models/                 # lbph_model.yml, labels.json
      intruders/              # Intruder snapshots
  PhoneApp/                   # Android app (Kotlin)
  main.py                     # Optional entrypoint
  README.md
```

---

## Setup

1. Clone the repository and open a terminal in the project root.

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

3. Install backend dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

   For face recognition (train/monitor), also install:

   ```bash
   pip install opencv-contrib-python
   ```

4. Optional: create `backend/personal.env` (or `personal.env` in project root) for alerts:

   ```env
   BACKEND_URL=https://your-backend.com/alerts
   API_KEY=your-optional-bearer-token
   ```

   If `BACKEND_URL` is not set, intruder payloads are printed to the console instead of POSTed.

---

## Usage

All commands are run from the **project root** so that `backend` is on the module path. Use `python -m` or `py -m` as appropriate for your system.

### 1. Enroll the owner

Capture at least 10 face images (200 samples by default). Only one face should be visible per frame.

```bash
python -m backend.camera.enroll
```

Images are saved under `backend/data/enrolled/owner/`. Press `q` to quit early.

### 2. Train the model (optional if you run the server)

If you run the server without an existing model, it will train once from enrolled images. To train manually:

```bash
python -m backend.camera.train_and_monitor train
```

This writes `backend/data/models/lbph_model.yml` and `labels.json`.

### 3. Run monitor only (no server)

```bash
python -m backend.camera.train_and_monitor monitor
```

Opens the camera window with owner/intruder boxes. Press `q` to quit (sends SIGINT; same effect as Ctrl+C).

### 4. Run the server (monitor + WebSocket)

Starts the camera monitor in a background thread and a WebSocket server on `0.0.0.0:12345`. If no model exists, training runs first.

```bash
python -m backend.server
```

- **Quit**: Press `q` in the monitor window to exit the whole process (same as Ctrl+C in the terminal).
- **WebSocket**: Clients can connect to `ws://<host>:12345`, receive `STATE` messages (payload: threat, fps, faces, image), and send `COMMAND` with action `LOCK` to trigger Windows lock (when `backend.services.lock` is used).

---

## Configuration

| Item | Location | Description |
|------|----------|-------------|
| Enrolled images | `backend/data/enrolled/owner/` | JPG/PNG; at least 10 for training. |
| Model / labels | `backend/data/models/` | `lbph_model.yml`, `labels.json`. |
| Intruder snapshots | `backend/data/intruders/` | Saved on intruder detection. |
| Backend URL / API key | `personal.env` | `BACKEND_URL`, `API_KEY` for HTTP alerts. |

---

## Android app

The `PhoneApp/` directory contains an Android (Kotlin) app that can connect to the backend WebSocket, show state, and send commands. Build and run from Android Studio or Gradle; configure the server host/port in the app (e.g. IP entry screen).

---

## Development notes

- **opencv-python vs opencv-contrib-python**: LBPH face recognizer lives in `cv2.face`, which is provided by `opencv-contrib-python`. The monitor will raise a clear error if `cv2.face` is missing.
- **Windows lock**: `backend/services.lock` uses `ctypes` and `LockWorkStation`; it only runs on Windows.
- **.gitignore**: The repo ignores `data/`, `*.env`, and common venv/cache paths so enrolled images, models, and secrets are not committed.

---

## License

See repository or project metadata for license terms.
