import serial
import time
from typing import Optional

class CubeController:
    def __init__(self, port, baudrate = 19200, timeout = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, self.timeout)
        time.sleep(0.2)

    def close(self):
        if self.ser:
            try: self.ser.close()
            except: pass
        self.ser = None

    def _send(self, cmd) -> str:
        if not self.ser:
            raise RuntimeError("CUBE not connected")
        full = (cmd+ "\r\n").encode('utf-8')
        self.ser.write(full)
        time.sleep(1)
        return self.ser.read_all().decode("utf-8", errors="ignore").strip()
    
    def on(self, power_mw=12.0):
        self._send("EXT=1")
        self._send("CW=1")
        self._send(f"P={power_mw}")
        self._send("L=1")
        time.sleep(3)

    def off(self):
        self._send("L=0")