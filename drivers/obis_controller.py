import serial
import time
from typing import Optional

class ObisController:
    def __init__(self, port: str, baudrate = 115200, timeout = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
    
    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, self.timeout)
        time.sleep(0.2)

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
        self.ser = None
    
    def _send(self, cmd: str) -> list[str]:
        if not self.ser:
            raise RuntimeError("OBIS not Connected")
        self.ser.write((cmd + '\r\n').encode())
        time.sleep(0.2)
        lines = self.ser.readlines()
        return [ln.decode(errors="ignore").strip() for ln in lines]
    
    def on(self, channel: int):
        self._send(f"SOUR{channel}:AM:STAT ON")

    def off(self, channel: int):
        self._send(f"SOUR{channel}:AM:STAT OFF")

    def set_power_w(self, channel: int, watts: float):
        self._send(f"SOUR{channel}:POW:LEV:IMM:AMPL {watts:.3f}")
        

        