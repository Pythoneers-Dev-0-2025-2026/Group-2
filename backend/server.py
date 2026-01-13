import socket
import app
import json
import os
from dotenv import load_dotenv
# this .env should have ip on there
load_dotenv() 

threat_detected = False # for testing
SERVERIP = os.getenv("SERVERIP")
request = { 
        # "threat_detection" : threat, needs to be realised from cv
        "lock_status": app.check_lock_status(), 
        "threat_detected" : threat_detected # this obviously will do nothing now
        }

HOST, PORT = SERVERIP, 12345
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


data = request
try:
    sock.connect((HOST, PORT))
    sock.sendall(json.dumps(data).encode("utf-8"))

    received = sock.recv(1024)
    received = json.loads(received.decode("utf-8"))

finally:
    sock.close()