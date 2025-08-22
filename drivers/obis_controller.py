# drivers/obis_controller.py
import serial
import serial.tools.list_ports
import time
from typing import Optional, List


class ObisController:
    """
    Minimal OBIS laser serial driver (SCPI-like).
    Keeps your original interface but fixes the PySerial kwargs bug and
    makes I/O a bit more robust.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port: str = port
        self.baudrate: int = int(baudrate)
        # PySerial expects timeout in seconds (float or None)
        self.timeout: Optional[float] = None if timeout in (None, "", "None") else float(timeout)
        self.ser: Optional[serial.Serial] = None

    # -----------------------------
    # Lifecycle
    # -----------------------------
    def connect(self):
        """
        Open the serial port. IMPORTANT: use keyword args so 'timeout' does not
        get misinterpreted as 'bytesize'.
        """
        self.close()  # ensure clean start

        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,             # <- keyword (fixes your error)
            write_timeout=self.timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )

        # Give the device a moment to be ready
        time.sleep(0.2)
        # Clear any residual input
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
        except Exception:
            pass

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    # -----------------------------
    # Low-level I/O helpers
    # -----------------------------
    def _ensure_open(self):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("OBIS not connected")

    def _write_line(self, line: str):
        self._ensure_open()
        # OBIS typically expects CR/LF; you used \r\n previously—keep that.
        data = (line + "\r\n").encode("ascii", errors="ignore")
        self.ser.write(data)
        self.ser.flush()

    def _read_all(self, idle_window: float = 0.08, max_time: Optional[float] = None) -> bytes:
        """
        Read until the input stream stays idle for 'idle_window' seconds or
        until 'max_time' (if provided) elapses.
        """
        self._ensure_open()
        start = time.monotonic()
        last_len = -1
        buf = bytearray()

        while True:
            chunk = self.ser.read(self.ser.in_waiting or 1)
            if chunk:
                buf += chunk

            # Stop if no growth for idle_window
            time.sleep(idle_window)
            if len(buf) == last_len:
                break
            last_len = len(buf)

            if max_time is not None and (time.monotonic() - start) > max_time:
                break

        return bytes(buf)

    def _send(self, cmd: str) -> List[str]:
        """
        Send a command and return all response lines (stripped).
        Mirrors your original behaviour but uses a more reliable read.
        """
        self._write_line(cmd)
        # Short dwell to allow device to answer
        time.sleep(0.05)
        raw = self._read_all(idle_window=0.05, max_time=self.timeout or 1.0)
        if not raw:
            return []
        # Normalize CR/LF and split
        text = raw.decode("ascii", errors="ignore").replace("\r", "")
        lines = [ln.strip() for ln in text.split("\n") if ln.strip() != ""]
        return lines

    # -----------------------------
    # High-level commands (your API)
    # -----------------------------
    def on(self, channel: int):
        self._send(f"SOUR{channel}:AM:STAT ON")

    def off(self, channel: int):
        self._send(f"SOUR{channel}:AM:STAT OFF")

    def set_power_w(self, channel: int, watts: float):
        self._send(f"SOUR{channel}:POW:LEV:IMM:AMPL {float(watts):.3f}")

    def is_present(self) -> bool:
        """
        Try both *IDN? and IDN? since firmwares vary.
        Returns True if the word 'OBIS' appears in the response.
        """
        try:
            res = self._send("*IDN?")
            if not res:
                res = self._send("IDN?")
            joined = " | ".join(res).upper()
            return "OBIS" in joined or "COHERENT" in joined
        except Exception:
            return False

    # -----------------------------
    # Convenience utilities
    # -----------------------------
    @staticmethod
    def list_ports() -> List[str]:
        """Helper to enumerate serial ports if you need it in UI."""
        return [p.device for p in serial.tools.list_ports.comports()]

    # Context manager for safe use
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
