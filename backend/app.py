import ctypes #provides windll functions
import time
import socket
import json
import os

# initialize as False
lock_status = False

request = { 
    "lock_status": lock_status, 

}

data = json.dumps(request)

# hostname = socket.gethostname() # store laptop name is hostname
# ip = socket.gethostbyname(hostname)
# print(ip)


def lock():  
 
    # kernel = ctypes.windll.
    ##testing
    status = bool(ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100))
    active_session_id = ctypes.windll.user32.WTSGetActiveConsoleSessionId()
    print(f"Initial Status: {status} {active_session_id}")
    ctypes.windll.user32.LockWorkStation()
    

    loop = True
    while loop:
        if bool(ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)) == False:
            time.sleep(2)
            loop = False
            # print(ctypes.windll.user32.WTSGetActiveConsoleSessionId())
            print("Logged In")

        # print(ctypes.windll.user32.WTSGetActiveConsoleSessionId())
        print("Not Logged In")
        time.sleep(1)
    


def proctor():
    pass


lock()


