"""
Train LBPH face model from enrolled owner images, then run monitor (owner vs intruder).
Run standalone once:
  From project root: python -m backend.camera.train_and_monitor train
  From project root: python -m backend.camera.train_and_monitor monitor
"""
import json
import os
import signal
import sys
import time
from datetime import datetime

import cv2
import numpy as np
import threading
import requests
from dotenv import load_dotenv
from collections import deque

# Imports: work when run as module or as script (python train_and_monitor.py)
def _setup_import_path():
    if __name__ == "__main__":
        _dir = os.path.dirname(os.path.abspath(__file__))
        _backend = os.path.dirname(_dir)
        if _backend not in sys.path:
            sys.path.insert(0, _backend)

_setup_import_path()

try:
    from .camera import get_frame, release_camera, encode_image
except ImportError:
    from camera.camera import get_frame, release_camera, encode_image

try:
    from .screenshots.screenshots import send_telegram_photo
except Exception:
    try:
        from camera.screenshots.screenshots import send_telegram_photo
    except Exception:
        def send_telegram_photo(path: str, caption: str) -> None:
            pass

# ───────────── SETTINGS ─────────────

# Data under backend/ so paths work from any cwd when run as module or script
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BACKEND_DIR, "data")

OWNER_NAME = "owner"
ENROLL_DIR = os.path.join(_DATA_DIR, "enrolled", OWNER_NAME)
MODEL_DIR = os.path.join(_DATA_DIR, "models")
INTRUDER_DIR = os.path.join(_DATA_DIR, "intruders")

MODEL_PATH = os.path.join(MODEL_DIR, "lbph_model.yml")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")

FACE_SIZE = (200, 200)
MIN_FACE_AREA = 80 * 80
INTRUDER_CONFIDENCE_THRESHOLD = 70.0
ALERT_COOLDOWN_SEC = 10
INTRUDER_STREAK_REQUIRED = 3

PROCESS_EVERY_N_FRAMES = 5
DOWNSCALE_FACTOR = 0.5
UPSCALE = int(1 / DOWNSCALE_FACTOR)
DECISION_WINDOW = 7
INTRUDER_VOTES_REQUIRED = 4

# ───────────── SHARED STATE ─────────────

# JSON-serializable for server; do not store numpy arrays here
LATEST_STATE = {
    "threat": False,
    "fps": 0.0,
    "image": None,
    "faces": [],
}

# ───────────── HELPERS ─────────────

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def get_face_cascade() -> cv2.CascadeClassifier:
    p = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    c = cv2.CascadeClassifier(p)
    if c.empty():
        raise RuntimeError("Haar cascade failed")
    return c


def get_lbph_recognizer():
    if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
        raise RuntimeError(
            "LBPH face recognizer not available. "
            "Install opencv-contrib-python (and uninstall opencv-python if present): "
            "pip install opencv-contrib-python"
        )
    return cv2.face.LBPHFaceRecognizer_create()


def load_images_for_owner():
    if not os.path.isdir(ENROLL_DIR):
        raise FileNotFoundError(f"Enrollment folder not found: {ENROLL_DIR}")

    paths = [
        os.path.join(ENROLL_DIR, f)
        for f in os.listdir(ENROLL_DIR)
        if f.lower().endswith((".jpg", ".png"))
    ]
    paths.sort()

    faces = []
    labels = []
    for p in paths:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img = cv2.resize(img, FACE_SIZE)
        faces.append(img)
        labels.append(0)

    if len(faces) < 10:
        raise RuntimeError(
            f"Not enough enrollment images. Need at least 10, found {len(faces)} in {ENROLL_DIR}"
        )
    return faces, labels


def train_model() -> None:
    ensure_dir(MODEL_DIR)
    faces, labels = load_images_for_owner()
    recognizer = get_lbph_recognizer()
    labels_np = np.array(labels, dtype=np.int32)
    recognizer.train(faces, labels_np)
    recognizer.save(MODEL_PATH)
    label_map = {"0": OWNER_NAME}
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(label_map, f, indent=2)
    print(f"|TRAIN| - Model saved: {MODEL_PATH}")
    print(f"|TRAIN| - Labels saved: {LABELS_PATH}")


def send_json(payload: dict) -> None:
    load_dotenv("personal.env")
    backend_url = (os.getenv("BACKEND_URL") or "").strip()
    api_key = (os.getenv("API_KEY") or "").strip()

    if not backend_url:
        print("[ALERT] BACKEND_URL not set. Printing JSON instead:")
        print(json.dumps(payload, indent=2))
        return

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        r = requests.post(backend_url, json=payload, headers=headers, timeout=5)
        print(f"[ALERT] Sent to backend. Status={r.status_code}")
    except Exception as e:
        print(f"[ALERT] Failed to send JSON: {e}")
        print(json.dumps(payload, indent=2))


def save_intruder_snapshot(frame) -> str:
    ensure_dir(INTRUDER_DIR)
    name = f"intruder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    path = os.path.join(INTRUDER_DIR, name)
    cv2.imwrite(path, frame)
    return path


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ───────────── CAMERA THREAD ─────────────

class CameraThread:
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        self.stop = False
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self.stop:
            frame = get_frame()
            if frame is not None:
                with self.lock:
                    self.frame = frame

    def get(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def shutdown(self):
        self.stop = True
        release_camera()


# ───────────── VISION THREAD ─────────────

class VisionThread:
    def __init__(self, camera: CameraThread):
        self.camera = camera
        self.stop = False
        self.cascade = get_face_cascade()
        self.recognizer = get_lbph_recognizer()
        self.recognizer.read(MODEL_PATH)
        self.vote_window = deque(maxlen=DECISION_WINDOW)
        self.last_intruder_crop = None
        self.prev_threat = False
        print("[VISION] Vision thread started")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        frame_count = 0
        while not self.stop:
            frame = self.camera.get()
            if frame is None:
                time.sleep(0.001)
                continue

            frame_count += 1
            if frame_count % PROCESS_EVERY_N_FRAMES != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, None, fx=DOWNSCALE_FACTOR, fy=DOWNSCALE_FACTOR)
            detections = self.cascade.detectMultiScale(small, 1.1, 5)

            faces_out = []
            intruder_seen = False

            for (x, y, w, h) in detections:
                x, y, w, h = map(lambda v: int(v * UPSCALE), (x, y, w, h))
                if w * h < MIN_FACE_AREA:
                    continue
                roi = gray[y : y + h, x : x + w]
                roi = cv2.resize(roi, FACE_SIZE)
                label, conf = self.recognizer.predict(roi)
                is_intruder = (label != 0) or (conf > INTRUDER_CONFIDENCE_THRESHOLD)
                faces_out.append({
                    "rect": (x, y, w, h),
                    "intruder": is_intruder,
                    "confidence": float(conf),
                })
                if is_intruder:
                    intruder_seen = True
                    self.last_intruder_crop = frame[y : y + h, x : x + w].copy()

            self.vote_window.append(1 if intruder_seen else 0)
            threat = sum(self.vote_window) >= INTRUDER_VOTES_REQUIRED

            if threat and not self.prev_threat and self.last_intruder_crop is not None:
                try:
                    LATEST_STATE["image"] = encode_image(self.last_intruder_crop)
                    print("[ALERT] Intruder detected (image captured)")
                except Exception:
                    pass

            self.prev_threat = threat
            LATEST_STATE["faces"] = faces_out
            LATEST_STATE["threat"] = threat

    def shutdown(self):
        self.stop = True


# ───────────── DRAWING ─────────────

def draw_faces(frame, faces):
    for f in faces:
        x, y, w, h = f["rect"]
        intruder = f["intruder"]
        conf = f["confidence"]
        color = (0, 0, 255) if intruder else (0, 255, 0)
        label = "INTRUDER" if intruder else "OWNER"
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            frame, f"{label} {conf:.1f}",
            (x, max(0, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
        )


# ───────────── MONITOR (main loop) ─────────────

def monitor(on_quit=None) -> None:
    """on_quit ignored; pressing 'q' sends SIGINT so the process exits like Ctrl+C."""
    ensure_dir(INTRUDER_DIR)
    if not os.path.isfile(MODEL_PATH):
        print("|MONITOR| - No model found. Training first...")
        train_model()

    print("[MONITOR] Camera starting")
    camera = CameraThread()
    vision = VisionThread(camera)

    last_alert_time = 0.0
    intruder_streak = 0
    last = time.time()
    fps = 0.0

    print("|MONITOR| - Running. Press 'q' to quit.")
    print(f"|MONITOR| - Intruder threshold = confidence > {INTRUDER_CONFIDENCE_THRESHOLD}")

    try:
        while True:
            frame = camera.get()
            if frame is None:
                continue

            if LATEST_STATE["threat"]:
                intruder_streak += 1
            else:
                intruder_streak = 0

            now = time.time()
            crop = vision.last_intruder_crop
            if (
                intruder_streak >= INTRUDER_STREAK_REQUIRED
                and (now - last_alert_time) >= ALERT_COOLDOWN_SEC
                and crop is not None
            ):
                snapshot_path = save_intruder_snapshot(crop)
                payload = {
                    "event": "intruder_detected",
                    "timestamp": iso_now(),
                    "confidence": 0.0,
                    "bbox": [0, 0, crop.shape[1], crop.shape[0]],
                    "snapshot_path": snapshot_path,
                }
                send_json(payload)
                caption = f"INTRUDER DETECTED\nTime: {iso_now()}"
                send_telegram_photo(snapshot_path, caption)
                last_alert_time = now
                intruder_streak = 0

            draw_faces(frame, LATEST_STATE["faces"])
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - last, 1e-6))
            last = now
            LATEST_STATE["fps"] = fps
            cv2.putText(
                frame, f"FPS: {fps:.1f}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
            )
            cv2.imshow("Monitor - Owner vs Intruder", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        vision.shutdown()
        camera.shutdown()
        cv2.destroyAllWindows()
        # Same as Ctrl+C: raise KeyboardInterrupt in main thread via SIGINT
        os.kill(os.getpid(), signal.SIGINT)


# Alias for server
def monitor_stream(on_quit=None):
    monitor(on_quit=on_quit)


def main() -> None:
    mode = "monitor"
    if len(sys.argv) >= 2:
        mode = sys.argv[1].strip().lower()

    if mode == "train":
        train_model()
    elif mode == "monitor":
        monitor()
    else:
        print("Usage:")
        print("  python -m backend.camera.train_and_monitor train")
        print("  python -m backend.camera.train_and_monitor monitor")


if __name__ == "__main__":
    main()
