import json
import os
import time
from datetime import datetime

import cv2
import numpy as np
import requests
from dotenv import load_dotenv

from .camera import get_frame, release_camera
from .screenshots.screenshots import send_telegram_photo

#settings
OWNER_NAME = "owner"
ENROLL_DIR = os.path.join("data", "enrolled", OWNER_NAME)
MODEL_DIR = os.path.join("data", "models")
INTRUDER_DIR = os.path.join("data", "intruders")

MODEL_PATH = os.path.join(MODEL_DIR, "lbph_model.yml")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")

FACE_SIZE = (200, 200)
MIN_FACE_AREA = 80 * 80

#can trial and error this if needed
INTRUDER_CONFIDENCE_THRESHOLD = 70.0

#for potential spam
ALERT_COOLDOWN_SEC = 10

#intruder in 3 frames before detecting
INTRUDER_STREAK_REQUIRED = 3


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


#haar cascade
def get_face_cascade() -> cv2.CascadeClassifier:
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        raise RuntimeError("Haar cascade failed")
    return cascade


def load_images_for_owner():
    if not os.path.isdir(ENROLL_DIR):
        raise FileNotFoundError(f"Enrollment folder not found: {ENROLL_DIR}")

    paths = [
        os.path.join(ENROLL_DIR, f)
        for f in os.listdir(ENROLL_DIR)
        if f.lower().endswith(".jpg") or f.lower().endswith(".png")
    ]
    paths.sort()

    faces = []
    labels = []

    # 0 = owner
    for p in paths:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img = cv2.resize(img, FACE_SIZE)
        faces.append(img)
        labels.append(0)

    if len(faces) < 10:
        raise RuntimeError(f"Not enough enrollment images to train. Found {len(faces)} images in {ENROLL_DIR}")

    return faces, labels


def get_lbph_recognizer():
    #LBPH in opencv-contrib-python
    #this for if user doesnt have it installed
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "cv2.face not found. You probably need opencv-contrib-python instead of opencv-python."
        )
    if not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
        raise RuntimeError(
            "LBPHFaceRecognizer_create not found. Install opencv-contrib-python."
        )
    return cv2.face.LBPHFaceRecognizer_create()

#RUN THIS FUNCTION TO TRAIN MODEL
def train_model():
    ensure_dir(MODEL_DIR)
    faces, labels = load_images_for_owner()

    recognizer = get_lbph_recognizer()
   
    labels_np = np.array(labels, dtype=np.int32)
    recognizer.train(faces, labels_np)
    recognizer.save(MODEL_PATH)
    #save label map
    label_map = {"0": OWNER_NAME}
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(label_map, f, indent=2)

    print(f"|TRAIN| - Trained model saved to: {MODEL_PATH}")
    print(f"|TRAIN| - Labels saved to: {LABELS_PATH}")

#----------------------------------------G SENDING JSON----------------------------------------
def send_json(payload: dict):
    #loads personal.env if present, prints JSON if fails
    load_dotenv("personal.env")

    backend_url = os.getenv("BACKEND_URL", "").strip()
    api_key = os.getenv("API_KEY", "").strip()  # optional

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

#---------------------------------------------------------------------------------------------


def iso_now():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def save_intruder_snapshot(frame) -> str:
    #saving intruder captures
    ensure_dir(INTRUDER_DIR)
    filename = os.path.join(INTRUDER_DIR, f"intruder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
    cv2.imwrite(filename, frame)
    return filename

#RUN THIS FUNCIOTN TO OPEN AND VIEW MONITOR
def monitor():
    ensure_dir(INTRUDER_DIR)

    if not os.path.isfile(MODEL_PATH):
        print("|MONITOR| - No model found. Training first...")
        train_model()

    recognizer = get_lbph_recognizer()
    recognizer.read(MODEL_PATH)

    face_cascade = get_face_cascade()

    last_alert_time = 0.0
    intruder_streak = 0

    print("|MONITOR| - Running. Press 'q' to quit.")
    print(f"|MONITOR| - Intruder threshold = confidence > {INTRUDER_CONFIDENCE_THRESHOLD} (lower = better match)")

    while True:
        frame = get_frame()
        if frame is None:
            print("|MONITOR| - Could not grab frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        display = frame.copy()

        intruder_detected_this_frame = False
        best_intruder_info = None

        for (x, y, w, h) in faces:
            if w * h < MIN_FACE_AREA:
                continue

            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, FACE_SIZE)

            label, confidence = recognizer.predict(face_roi)

            #0 is owner and higher the confidence less likely to be owner
            is_intruder = (label != 0) or (confidence > INTRUDER_CONFIDENCE_THRESHOLD)

            #UI box and confidence status
            color = (0, 0, 255) if is_intruder else (0, 255, 0)
            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)

            tag = f"{'INTRUDER' if is_intruder else 'OWNER'}  conf={confidence:.1f}"
            cv2.putText(display, tag, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if is_intruder:
                intruder_detected_this_frame = True
                best_intruder_info = (x, y, w, h, float(confidence))

        #intruder streak logic to reduce false positives
        if intruder_detected_this_frame:
            intruder_streak += 1
        else:
            intruder_streak = 0

        #alert only when streak reached and cooldown passed
        now = time.time()
        if best_intruder_info and intruder_streak >= INTRUDER_STREAK_REQUIRED and (now - last_alert_time) >= ALERT_COOLDOWN_SEC:
            (x, y, w, h, confidence) = best_intruder_info
            snapshot_path = save_intruder_snapshot(frame)

            payload = {
                "event": "intruder_detected",
                "timestamp": iso_now(),
                "confidence": confidence,
                "bbox": [int(x), int(y), int(w), int(h)],
                "snapshot_path": snapshot_path,
            }

            send_json(payload)
            
            # Send Telegram notification with screenshot
            caption = f"⚠️ INTRUDER DETECTED!\nConfidence: {confidence:.1f}\nTime: {iso_now()}"
            send_telegram_photo(snapshot_path, caption)
            
            last_alert_time = now
            intruder_streak = 0  # reset after alert
            return json.dumps(payload)

        cv2.imshow("Monitor - Owner vs Intruder", display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        
    release_camera()
    cv2.destroyAllWindows()


def main():
    import sys
    mode = "monitor"
    if len(sys.argv) >= 2:
        mode = sys.argv[1].strip().lower()

    if mode == "train":
        train_model()
    elif mode == "monitor":
        monitor()
    else:
        print("Usage:")
        print("  python train_and_monitor.py train")
        print("  python train_and_monitor.py monitor")


if __name__ == "__main__":
    main()
