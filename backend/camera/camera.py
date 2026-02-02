import cv2

cap = cv2.VideoCapture(0)
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
