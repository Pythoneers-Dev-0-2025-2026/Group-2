import cv2
import time
import os
import base64
from typing import Optional, Dict


def encode_frame_to_base64(frame) -> str:
    """
    Encode an OpenCV frame to a base64 JPEG string.
    """
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise ValueError("Failed to encode image")

    return base64.b64encode(buffer).decode("utf-8")


def save_frame(
    frame,
    folder: str = "screenshots",
    prefix: str = "intruder"
) -> str:
    """
    Save an OpenCV frame to disk.
    Returns the saved file path.
    """
    os.makedirs(folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(folder, f"{prefix}_{timestamp}.jpg")

    cv2.imwrite(path, frame)
    print(f"[SCREENSHOT] Saved to: {path}")

    return path


def stage_image_payload(
    frame,
    save: bool = False,
    folder: str = "screenshots"
) -> Dict[str, Optional[str]]:
    """
    Prepare image data for JSON transmission.

    Returns a dict with:
    - image: base64 string
    - timestamp: ISO-ish timestamp
    - saved_path: optional local file path
    """
    payload = {
        "image": None,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "saved_path": None
    }

    payload["image"] = encode_frame_to_base64(frame)

    if save:
        payload["saved_path"] = save_frame(frame, folder)

    return payload
