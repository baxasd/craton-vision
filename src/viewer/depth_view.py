import cv2
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtGui import QIcon, QImage, QPixmap
from src.utils.theme import ICON_PATH
from src.viewer.components import (
    BG_BASE, FONT, Panel, FillLabel
)
from src.viewer.workers import ZmqCameraWorker

class DepthStreamWindow(QMainWindow):
    def __init__(self, ip: str):
        super().__init__()
        self.publisher_ip = ip
        self.setWindowTitle(f"Depth Map  ·  {ip}")
        self.resize(800, 600)
        self.setWindowIcon(QIcon(ICON_PATH))

        self._apply_style()
        self._build_ui()
        self._start_worker()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {BG_BASE};
                font-family: '{FONT}';
            }}
        """)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(16, 16, 16, 16)

        panel = Panel("Depth Map")
        self.depth_feed = FillLabel()
        panel.body().addWidget(self.depth_feed)
        
        lay.addWidget(panel)

    def _start_worker(self):
        self.worker = ZmqCameraWorker(self.publisher_ip)
        self.worker.new_frame.connect(self._on_frame)
        self.worker.start()

    def _on_frame(self, meta: dict, img_bytes: bytes, depth_bytes: bytes):
        if depth_bytes:
            arr   = np.frombuffer(depth_bytes, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt    = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            self.depth_feed.set_pixmap(QPixmap.fromImage(qt))

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()
