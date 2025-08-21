import sys, traceback
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from ..core.config import AppConfig, DEFAULT_CONFIG, load_config
from ..core.measurement import MeasurementRunner
from .run_plan_widget import RunPlanWidget
from .live_view import LiveView
from .analysis_view import AnalysisView

class MeasureWorker(QObject):
    live = pyqtSignal(object, float, float, str)
    finished = pyqtSignal(str)
    errored = pyqtSignal(str)

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            runner = MeasurementRunner(self.cfg)
            res = runner.run(on_live=lambda y, peak, it, lid: self.live.emit(y, peak, it, lid))
            self.finished.emit(res.run_dir)
        except Exception as e:
            tb = traceback.format_exc()
            self.errored.emit(f"{e}\n{tb}")

class MainWindow(QWidget):
    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.setWindowTitle("SciLab")
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        self.plan = RunPlanWidget(cfg, self)
        self.live = LiveView(self)
        self.analysis = AnalysisView(self)

        tabs.addTab(self.plan, "Run Plan")
        tabs.addTab(self.live, "Live View")
        tabs.addTab(self.analysis, "Analysis")

        self.plan.startClicked.connect(self.start_measurement)

        self._thread: QThread | None = None
        self._worker: MeasureWorker | None = None
        self._cfg = cfg

    def start_measurement(self):
        if self._thread:
            QMessageBox.warning(self, "Busy", "Measurement already running.")
            return
        self._thread = QThread(self)
        self._worker = MeasureWorker(self._cfg)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.live.connect(self.live.update_live)
        self._worker.finished.connect(self._on_finished)
        self._worker.errored.connect(self._on_error)
        self._thread.start()

    def _on_finished(self, run_dir: str):
        QMessageBox.information(self, "Done", f"Run saved at:\n{run_dir}")
        self._cleanup()

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)
        self._cleanup()

    def _cleanup(self):
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None

def main():
    try:
        cfg = load_config("SciLab.yaml") #if it is present
    except Exception:
        cfg = DEFAULT_CONFIG

    app = QApplication(sys.argv)
    w = MainWindow(cfg)
    w.resize(1100, 800)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
