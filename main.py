import json

from backend.services import lock
from backend.camera.train_and_monitor import main

if __name__ == "__main__":
    payload = main()
    data = payload