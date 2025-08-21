from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import pyqtSlot
import plotly.graph_objs as go
import plotly.io as pio
import numpy as np

class LiveView(QWidget):
    """Plotly in QWebEngineView for live spectrum display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.web = QWebEngineView(self)
        self.layout.addWidget(self.web, 1) # Set stretch factor to 1
        self._fig = go.Figure()
        self._fig.update_layout(title_text="Live Spectrum")
        self._fig.add_trace(go.Scatter(y=[0], mode="lines", name="spectrum"))
        self._push_fig()

    def _push_fig(self):
        html = pio.to_html(self._fig, full_html=True, include_plotlyjs="cdn")
        # Directly set HTML (no QUrl / temp file needed)
        self.web.setHtml(html)

    @pyqtSlot(object, float, float, str)
    def update_live(self, y: object, peak: float, it_ms: float, label: str):
        if isinstance(y, np.ndarray) and y.size:
            self._fig.data = []
            self._fig.add_trace(go.Scatter(y=y.tolist(), mode="lines", name=f"{label}"))
            self._fig.update_layout(title=f"Live: {label} | peak={peak:.0f} | IT={it_ms:.2f} ms")
            self._push_fig()
