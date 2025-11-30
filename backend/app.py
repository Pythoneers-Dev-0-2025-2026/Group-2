import ctypes #provides windll functions
import time
import socket

hostname = socket.gethostname() # store laptop name is hostname
ip = socket.gethostbyname(hostname)
print(ip)



def lock():
    
    ## camera will detect something, call lock -> 

    ## lock will run and send a message to the users phone asking if they want to lock ->

    ## y -> lock

    ## n -> return

    ctypes.windll.user32.LockWorkStation()
    # this call locks the computer, and we want to lock user input as well


def proctor():
    pass





