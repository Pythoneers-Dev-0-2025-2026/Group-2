import ctypes #provides windll functions
import subprocess
import time
import socket # will be used to send data between phone and laptop
import json
import os


wtsapi32 = ctypes.windll.wtsapi32

user32 = ctypes.windll.user32
# print(user32)

def lock():
    """
    Locks windows workstation, sets lock_status to True
    """
    user32.LockWorkStation()
    check_lock_status()
    return None

def check_lock_status():
    """
    Returns the current boolean value of a computers lock status.
    Checks task manager for LogonUi.exe

    Locked -> True
    Unlocked -> False
    """
    output = subprocess.check_output('TASKLIST').decode()
    if 'LogonUI.exe' in output:
        return True
    return False
    
# def proctor():


if __name__ == "__main__": 
    
    threat_detected = False # will change to the response of the camera

    ## testing
    lock()
    
    while True:

        request = { 
            # "threat_detection" : threat, needs to be realised from cv
            "lock_status": check_lock_status(), 
            "threat_detected" : threat_detected # this obviously will do nothing now
        }
        data = json.dumps(request)

        if check_lock_status() == True:
            print("Locked")
        else:
            print("Unlocked")
        print(data)
        time.sleep(0.5)
    




