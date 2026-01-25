# Copilot Instructions for Group-2

## Project Overview
**Group-2** is a Python-based facial recognition security system that monitors for authorized users via webcam and triggers alerts when unknown faces (intruders) are detected. It uses Haar cascades for face detection and LBPH (Local Binary Patterns Histograms) for face recognition.

## Architecture

### Core Workflow
1. **Enrollment** (`camera/enroll.py`): User captures 50 face samples in varied poses/expressions
2. **Training** (`camera/train_and_monitor.py`): Trains LBPH model on enrolled faces
3. **Monitoring** (`camera/train_and_monitor.py`): Continuous webcam monitoring; detects intruders after 3-frame confirmation
4. **Alerts** (`camera/train_and_monitor.py` + `screenshots/screenshots.py`): 
   - Sends JSON payload to backend (`BACKEND_URL` from `personal.env`)
   - Sends Telegram notification with screenshot of intruder

### Key Modules
- **`camera/camera.py`**: Raw OpenCV camera interface (get_frame, release_camera)
- **`camera/enroll.py`**: Face enrollment with auto-capture and size filtering
- **`camera/train_and_monitor.py`**: LBPH model training + real-time monitoring loop with streak logic
- **`camera/screenshots/screenshots.py`**: Telegram integration for intruder notifications
- **`backend/app.py`**: Desktop lock mechanism via `ctypes.windll.user32.LockWorkStation()`

### Data Flow
```
Webcam → Face Detection (Haar) → Face Recognition (LBPH)
  ↓
  └─→ Owner? → Continue monitoring
  └─→ Intruder? (3-frame streak) → Save snapshot → Send alerts (Backend + Telegram)
```

## Configuration

All environment variables are stored in `personal.env` (Git-ignored):
- `BACKEND_URL`: HTTP endpoint for alert JSON payload
- `API_KEY`: Optional Bearer token for backend auth
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for photo notifications
- `TELEGRAM_CHAT_ID`: Telegram recipient chat ID

## Key Patterns & Conventions

### Face Detection/Recognition
- **Face size validation**: `MIN_FACE_AREA = 80*80` pixels to reject background faces
- **Face standardization**: All captured/processed faces resized to `(200, 200)`
- **Haar cascade**: Uses default frontalface detector; located at `cv2.data.haarcascades`
- **LBPH requirements**: Needs `opencv-contrib-python` (not standard `opencv-python`)

### Intruder Detection Logic
- **Streak-based**: Intruder must be detected in 3 consecutive frames before alerting (line ~200 in train_and_monitor.py)
- **Confidence threshold**: `INTRUDER_CONFIDENCE_THRESHOLD = 50.0` (LBPH distance metric)
- **Spam prevention**: `ALERT_COOLDOWN_SEC = 10` seconds between alerts

### Directory Structure
```
data/
  enrolled/owner/           # 50+ .jpg face samples for training
  models/
    lbph_model.yml         # Trained LBPH model
    labels.json            # {"0": "owner"} mapping
  intruders/               # Timestamped snapshots of unknown faces
```

## Development Workflows

### Common Tasks
1. **Enroll new user**: `python camera/enroll.py` → captures to `data/enrolled/owner/`
2. **Train model**: `python -c "from camera.train_and_monitor import train_model; train_model()"`
3. **Start monitoring**: `python -c "from camera.train_and_monitor import monitor; monitor()"`
4. **Test without backend**: Set invalid `BACKEND_URL` in `personal.env` → JSON prints to console

### Dependencies
Install via `requirements.txt`:
- `opencv-python` or `opencv-contrib-python` (must use contrib for LBPH)
- `mediapipe`, `requests`, `python-dotenv`

### Error Handling Patterns
- **Camera failures**: Gracefully return `None` in `get_frame()`, checked by caller
- **Missing model**: Auto-trains if `MODEL_PATH` doesn't exist (line ~175 in train_and_monitor.py)
- **Backend offline**: Falls back to printing JSON to console (see `send_json()` function)

## Important Notes for AI Agents
- Always check if `cv2.face` module exists before calling LBPH functions (runtime check at line ~80-88)
- Enrollment path is hardcoded as `data/enrolled/owner/` - changing requires updating 3+ locations
- Intruder streak counter must reset when authorized user is detected
- Timestamps use ISO format with timezone: `datetime.now().astimezone().isoformat()`
- Face detection params (scaleFactor=1.1, minNeighbors=5) are tuned for frontal faces; adjust if profile detection needed
