import logging, sys

def _default_logger() -> logging.Logger:
    lg = logging.getLogger("SciLab.drivers")
    if not lg.handlers:  # avoid duplicate handlers
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
        lg.addHandler(h)
        lg.setLevel(logging.INFO)
    return lg

# Public default logger other modules can import
LOGGER = _default_logger()
