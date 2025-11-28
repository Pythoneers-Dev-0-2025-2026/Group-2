import cv2
cam = cv2.VideoCapture(0)

def get_frame():
    ret, frame = cam.read()
    if not ret:
        return None
    return frame
if __name__ == "__main__":
    if not cam.isOpened():
        print("Error: Could not access camera")
        exit()

    while True:
        frame = get_frame()

        if frame is None:
            print("Failed to grab frame")
            break

        cv2.imshow("Camera Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
