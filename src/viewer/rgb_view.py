import cv2
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtGui import QIcon, QImage, QPixmap
from src.utils.theme import ICON_PATH, COLOR_LEFT, COLOR_RIGHT, COLOR_CENTER
from src.viewer.components import (
    BG_BASE, FONT, Panel, FillLabel, TEXT_PRI
)
from src.viewer.workers import ZmqCameraWorker

class RGBStreamWindow(QMainWindow):
    def __init__(self, ip: str):
        super().__init__()
        self.publisher_ip = ip
        self.setWindowTitle(f"RGB Camera  ·  {ip}")
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

        panel = Panel("RGB Camera")
        self.cam_feed = FillLabel()
        panel.body().addWidget(self.cam_feed)
        
        lay.addWidget(panel)

    def _start_worker(self):
        self.worker = ZmqCameraWorker(self.publisher_ip)
        self.worker.new_frame.connect(self._on_frame)
        self.worker.start()

    def _draw_clean_skeleton(self, frame, meta: dict):
        def hex_to_bgr(hx):
            hx = hx.lstrip('#')
            if len(hx) == 3:
                hx = ''.join([c*2 for c in hx])
            rgb = tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))
            return (rgb[2], rgb[1], rgb[0])

        CV_LEFT   = hex_to_bgr(COLOR_LEFT)
        CV_RIGHT  = hex_to_bgr(COLOR_RIGHT)
        CV_CENTER = hex_to_bgr(COLOR_CENTER)
        
        try:
            BLACK = hex_to_bgr(TEXT_PRI)
        except:
            BLACK = (48, 49, 50)
            
        GRAY      = (200, 198, 196)

        pts = {}
        for i in range(33):
            kx, ky = f"j{i}_px", f"j{i}_py"
            if kx in meta and ky in meta:
                pts[i] = (int(meta[kx]), int(meta[ky]))

        conns = [
            (0,1),(1,2),(2,3),(3,7),(0,4),(4,5),(5,6),(6,8),(9,10),
            (11,12),(11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
            (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
            (11,23),(12,24),(23,24),
            (23,25),(25,27),(27,29),(29,31),(31,27),
            (24,26),(26,28),(28,30),(30,32),(32,28),
        ]

        for p1, p2 in conns:
            if p1 in pts and p2 in pts:
                cv2.line(frame, pts[p1], pts[p2], GRAY, 3, cv2.LINE_AA)

        for i, (cx, cy) in pts.items():
            color = CV_CENTER if i == 0 else (CV_LEFT if i % 2 != 0 else CV_RIGHT)
            cv2.circle(frame, (cx, cy), 5, BLACK, 1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 4, color, -1, cv2.LINE_AA)
        return frame

    def _on_frame(self, meta: dict, img_bytes: bytes, depth_bytes: bytes):
        if img_bytes:
            arr   = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            frame = self._draw_clean_skeleton(frame, meta)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt    = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            self.cam_feed.set_pixmap(QPixmap.fromImage(qt))

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()
