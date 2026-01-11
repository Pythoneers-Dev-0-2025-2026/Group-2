import cv2
import mediapipe as mp
from .camera import get_frame #A
from .camera import release_camera #A
from .screenshots import save_and_send #A


mp_face = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

face_detector = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.3)

while True:
    frame = get_frame()

    if frame is None:
        print("Could not grab frame")
        break

    #rgb conversion
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = face_detector.process(img)

    #boxes
    if faces.detections:
        for detection in faces.detections:
            mp_drawing.draw_detection(frame, detection)
            save_and_send(frame) #A

    #display (just for me to test)
    cv2.imshow("Face Detectionq", frame)

    #to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        release_camera() #A
        break

cv2.destroyAllWindows()
