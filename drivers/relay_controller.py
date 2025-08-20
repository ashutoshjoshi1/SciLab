import serial
import time
from typing import Optional

class RelayController:
    def __init__(self, port, baudrate = 9600, timeout = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
    
    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout) 
        time.sleep(0.2)

    def close(self):
        if self.ser:
            try: self.ser.close()
            except: pass
        self.ser = None

    def on(self, n):
        if not self.ser:
            raise RuntimeError("Relay is not connected")
        self.ser.write(f"R{n}S\r".encode())
    
    def off(self, n):
        if not self.ser:
            raise RuntimeError("Relay is not connected")
        self.ser.write(f"R{n}R\r".encode())