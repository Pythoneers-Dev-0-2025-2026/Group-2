from camera.train_and_monitor import main
from backend.app import lock
import json

if __name__ == "__main__":
    payload = main()
    data = json.loads(payload.event)
    lock(data["event"])