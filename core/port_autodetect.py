from typing import Dict, Optional
import serial.tools.list_ports
from ..drivers.obis_controller import ObisController
from ..drivers.cube_controller import CubeController

def autodetect_ports() -> Dict[str, Optional[str]]:
    ports = [p.device for p in serial.tools.list_ports.comports()]
    res: Dict[str, Optional[str]] = {"obis_port": None, "cube_port": None}

    for p in ports:
        # Check for OBIS
        try:
            obis = ObisController(port=p)
            obis.connect()
            if obis.is_present():
                res["obis_port"] = p
                continue # Found it, don't check for CUBE
        except:
            pass
        finally:
            if "obis" in locals() and obis: obis.close()

        # Check for CUBE
        try:
            cube = CubeController(port=p)
            cube.connect()
            if cube.is_present():
                res["cube_port"] = p
        except:
            pass
        finally:
            if "cube" in locals() and cube: cube.close()

    return res
