import json

from backend.app import lock
from camera.train_and_monitor import main

if __name__ == "__main__":
    payload = main()
    data = payload
    lock()