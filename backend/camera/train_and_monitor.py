import os
import cv2
import time
import threading
import numpy as np
from collections import deque

from .camera import get_frame, release_camera, encode_image

# ───────────── SHARED STATE ─────────────

LATEST_STATE = {
    "threat": False,
    "fps": 0.0,
    "image": None,
    "faces": []
}

# ───────────── SETTINGS ─────────────

FACE_SIZE = (200, 200)
MIN_FACE_AREA = 80 * 80

PROCESS_EVERY_N_FRAMES = 5
DOWNSCALE_FACTOR = 0.5
UPSCALE = int(1 / DOWNSCALE_FACTOR)

INTRUDER_CONFIDENCE_THRESHOLD = 70.0
DECISION_WINDOW = 7
INTRUDER_VOTES_REQUIRED = 4

MODEL_PATH = "data/models/lbph_model.yml"

# ───────────── FACE SETUP ─────────────

def get_face_cascade():
    return cv2.CascadeClassifier(
        os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    )

def get_lbph():
    return cv2.face.LBPHFaceRecognizer_create()

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
    def __init__(self, camera):
        self.camera = camera
        self.stop = False

        self.cascade = get_face_cascade()
        self.recognizer = get_lbph()
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

                roi = gray[y:y+h, x:x+w]
                roi = cv2.resize(roi, FACE_SIZE)

                label, conf = self.recognizer.predict(roi)
                is_intruder = (label != 0) or (conf > INTRUDER_CONFIDENCE_THRESHOLD)

                faces_out.append({
                    "rect": (x, y, w, h),
                    "intruder": is_intruder,
                    "confidence": float(conf)
                })

                if is_intruder:
                    intruder_seen = True
                    self.last_intruder_crop = frame[y:y+h, x:x+w].copy()

            self.vote_window.append(1 if intruder_seen else 0)
            threat = sum(self.vote_window) >= INTRUDER_VOTES_REQUIRED

            # Send image ONCE per intrusion
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

        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(
            frame,
            f"{label} {conf:.1f}",
            (x, max(0, y-8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )

# ───────────── MAIN LOOP ─────────────

def monitor_stream():
    print("[MONITOR] Camera starting")
    camera = CameraThread()
    vision = VisionThread(camera)

    last = time.time()
    fps = 0.0

    try:
        while True:
            frame = camera.get()
            if frame is None:
                continue

            draw_faces(frame, LATEST_STATE["faces"])

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - last, 1e-6))
            last = now
            LATEST_STATE["fps"] = fps

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.imshow("Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        vision.shutdown()
        camera.shutdown()
        cv2.destroyAllWindows()
