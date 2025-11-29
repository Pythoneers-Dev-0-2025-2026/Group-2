import ctypes #provides windll functions
import time


def lock():
    
    ## camera will detect something, call lock -> 

    ## lock will run and send a message to the users phone asking if they want to lock ->

    ## y -> lock

    ## n -> return

    ctypes.WinDLL.user32.LockWorkStation() # this call locks the computer



lock()