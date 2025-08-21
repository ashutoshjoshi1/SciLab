from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.io as pio
from ..core.analysis import analyze_run

class AnalysisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.btnRow = QHBoxLayout()
        self.btnLoad = QPushButton("Load run (frames.parquet)")
        self.btnRow.addWidget(self.btnLoad)
        self.layout.addLayout(self.btnRow)

        self.lbl = QLabel("No run loaded.")
        self.layout.addWidget(self.lbl)

        self.web = QWebEngineView(self)
        self.layout.addWidget(self.web)

        self.btnLoad.clicked.connect(self._pick_and_analyze)

    def _set_fig(self, fig):
        html = pio.to_html(fig, full_html=True, include_plotlyjs="cdn")
        self.web.setHtml(html)

    def _pick_and_analyze(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select frames.parquet", "", "Parquet (*.parquet)")
        if not path: return
        self.lbl.setText(path)
        res = analyze_run(path)
        self._set_fig(res["figs"]["resolution"])
