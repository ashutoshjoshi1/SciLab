from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit
)
from PyQt5.QtCore import pyqtSignal, Qt
from ..core.config import AppConfig
from ..core.port_autodetect import autodetect_ports

class RunPlanWidget(QWidget):
    startClicked = pyqtSignal()

    def __init__(self, cfg: AppConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        layout = QVBoxLayout(self)

        ports_layout = QHBoxLayout()
        ports_layout.addWidget(QLabel("OBIS Port:"))
        self.obis_port_edit = QLineEdit(self.cfg.serial.obis_port)
        self.obis_port_edit.textChanged.connect(self._on_obis_port_changed)
        ports_layout.addWidget(self.obis_port_edit)

        ports_layout.addWidget(QLabel("CUBE Port:"))
        self.cube_port_edit = QLineEdit(self.cfg.serial.cube_port)
        self.cube_port_edit.textChanged.connect(self._on_cube_port_changed)
        ports_layout.addWidget(self.cube_port_edit)
        
        ports_layout.addStretch(1)

        self.rescan_btn = QPushButton("Rescan Ports")
        self.rescan_btn.clicked.connect(self._rescan_ports)
        ports_layout.addWidget(self.rescan_btn)

        layout.addLayout(ports_layout)


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

    def _on_obis_port_changed(self, text: str):
        self.cfg.serial.obis_port = text

    def _on_cube_port_changed(self, text: str):
        self.cfg.serial.cube_port = text

    def _rescan_ports(self):
        detected_ports = autodetect_ports()
        self.cfg.serial.obis_port = detected_ports["obis_port"]
        self.cfg.serial.cube_port = detected_ports["cube_port"]
        self.obis_port_edit.setText(self.cfg.serial.obis_port)
        self.cube_port_edit.setText(self.cfg.serial.cube_port)

    def on_measurement_started(self):
        self.obis_port_edit.setEnabled(False)
        self.cube_port_edit.setEnabled(False)
        self.rescan_btn.setEnabled(False)

    def on_measurement_finished(self):
        self.obis_port_edit.setEnabled(True)
        self.cube_port_edit.setEnabled(True)
        self.rescan_btn.setEnabled(True)
