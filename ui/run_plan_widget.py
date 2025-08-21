from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import pyqtSignal, Qt
from ..core.config import AppConfig

class RunPlanWidget(QWidget):
    startClicked = pyqtSignal()

    def __init__(self, cfg: AppConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Run Plan</b>"))
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Enabled", "ID (nm)", "Type", "Channel/Relay", "Power (W/mW)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btns = QHBoxLayout()
        self.btnStart = QPushButton("Start Measurement")
        btns.addStretch(1)
        btns.addWidget(self.btnStart)
        layout.addLayout(btns)

        self.btnStart.clicked.connect(self.startClicked.emit)
        self.refresh()

    def refresh(self):
        lasers = self.cfg.lasers
        self.table.setRowCount(len(lasers))
        for r, ls in enumerate(lasers):
            enabled = QTableWidgetItem("Yes" if ls.enabled else "No")
            enabled.setFlags(enabled.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(r, 0, enabled)

            idit = QTableWidgetItem(ls.id)
            idit.setFlags(idit.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(r, 1, idit)

            typ = QTableWidgetItem(ls.type)
            typ.setFlags(typ.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(r, 2, typ)

            ch = ""
            if ls.type == "OBIS" and ls.channel is not None: ch = str(ls.channel)
            if ls.type == "RELAY" and ls.relay_channel is not None: ch = str(ls.relay_channel)
            cell = QTableWidgetItem(ch); cell.setFlags(cell.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(r, 3, cell)

            pw = ""
            if ls.type == "OBIS" and ls.power_w is not None: pw = f"{ls.power_w:.6f} W"
            if ls.type == "CUBE" and ls.power_mw is not None: pw = f"{ls.power_mw:.1f} mW"
            cell2 = QTableWidgetItem(pw); cell2.setFlags(cell2.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(r, 4, cell2)
