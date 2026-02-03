import cv2
import time
import os
import requests
from dotenv import load_dotenv

# Load Telegram configuration from project root
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "personal.env")
load_dotenv(env_path)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def send_telegram_photo(image_path: str, caption: str = "Unfamiliar face detected!") -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("[TELEGRAM] Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured in personal.env")
        return False
    
    if not os.path.isfile(image_path):
        print(f"[TELEGRAM] Error: Image file not found: {image_path}")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    try:
        with open(image_path, "rb") as img:
            files = {"photo": img}
            data = {"chat_id": CHAT_ID, "caption": caption}
            response = requests.post(url, files=files, data=data, timeout=10)
        
        if response.status_code == 200:
            print(f"[TELEGRAM] Photo sent successfully: {image_path}")
            return True
        else:
            print(f"[TELEGRAM] Failed to send photo. Status={response.status_code}, Response={response.text}")
            return False
    except Exception as e:
        print(f"[TELEGRAM] Error sending photo: {e}")
        return False


def save_and_send(frame, folder="screenshots", caption="Unfamiliar face detected!"):
    # Save screenshot
    os.makedirs(folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(folder, f"unknown_{timestamp}.jpg")
    cv2.imwrite(path, frame)
    print(f"[SCREENSHOT] Saved to: {path}")
    
    # Send via Telegram
    send_telegram_photo(path, caption)
    
    return path
