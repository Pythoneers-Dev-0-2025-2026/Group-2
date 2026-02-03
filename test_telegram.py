import os
import requests
from dotenv import load_dotenv

# Load credentials
env_path = os.path.join(os.path.dirname(__file__), "personal.env")
load_dotenv(env_path)

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

print(f"Token loaded: {token[:20]}..." if len(token) > 20 else token)
print(f"Chat ID loaded: {chat_id}")

if not token or not chat_id:
    print("ERROR: Missing credentials in personal.env")
else:
    # Test if bot is valid
    response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
    print(f"\nBot validation response: {response.status_code}")
    print(response.json())
