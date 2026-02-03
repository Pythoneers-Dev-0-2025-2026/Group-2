import os
import time
import cv2

from camera import get_frame, release_camera


#settings
OWNER_NAME = "owner"
SAVE_DIR = os.path.join("data", "enrolled", OWNER_NAME)
NUM_SAMPLES = 200
FACE_SIZE = (200, 200)
MIN_FACE_AREA = 80 * 80 #dont capture small faces
AUTO_CAPTURE_EVERY_SEC = 0.20


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def get_face_cascade() -> cv2.CascadeClassifier:
    #load face finder
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        raise RuntimeError("Failed to load Haar cascade for face detection.")
    return cascade


def largest_face(faces):
    #to pickup only user and not small faces in background
    #faces are (x, y, w, h)
    return max(faces, key=lambda b: b[2] * b[3])


def main():
    ensure_dir(SAVE_DIR)
    face_cascade = get_face_cascade()

    saved = 0
    last_capture = 0.0

    print(f"|ENROLL| - Saving samples to: {SAVE_DIR}")
    print("|ENROLL| - Move head left, right, vary expressions slightly.")
    print("|ENROLL| - Press 'q' to quit early.")

    while saved < NUM_SAMPLES:
        frame = get_frame()
        if frame is None:
            print("|ENROLL| - Could not grab frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        now = time.time()

        if len(faces) == 1:
            #only save when theres one face
            (x, y, w, h) = faces[0]
            if w * h >= MIN_FACE_AREA and (now - last_capture) >= AUTO_CAPTURE_EVERY_SEC:
                face_roi = gray[y:y+h, x:x+w]
                face_roi = cv2.resize(face_roi, FACE_SIZE)

                filename = os.path.join(SAVE_DIR, f"img_{saved:04d}.jpg")
                cv2.imwrite(filename, face_roi)

                saved += 1
                last_capture = now

        #box around users face
        display = frame.copy()
        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(
            display,
            f"Enrolling: {saved}/{NUM_SAMPLES} (need exactly 1 face)",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.imshow("Enroll - Owner Face", display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    release_camera()
    cv2.destroyAllWindows()
    print(f"[ENROLL] Done. Captured {saved} samples.")


if __name__ == "__main__":
    main()
