import cv2
import base64

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def get_frame():
    if not cap.isOpened():
        print("Camera not opened")
        return None

    ret, frame = cap.read()
    if not ret:
        return None
    return frame

def release_camera():
    if cap.isOpened():
        cap.release()
        cv2.destroyAllWindows()

def encode_image(frame) -> str:
    """
    Encode OpenCV frame to base64 JPEG
    """
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise RuntimeError("Failed to encode frame")
    return base64.b64encode(buffer).decode("utf-8")
