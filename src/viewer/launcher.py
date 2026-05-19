import configparser
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, 
    QHBoxLayout, QLineEdit, QFrame
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from src.radar.parse import RadarConfig
from src.utils.theme import ICON_PATH, SETTINGS_PATH
from src.viewer.components import (
    BG_BASE, BG_SURF, TEXT_PRI, TEXT_SEC, PRIMARY, FONT, BORDER, 
    C_GREEN
)
from src.viewer.workers import (
    ZmqKeyWorker, ZmqRadarWorker, ZmqCameraWorker
)
from src.viewer.radar_view import RadarStreamWindow
from src.viewer.rgb_view import RGBStreamWindow
from src.viewer.depth_view import DepthStreamWindow

# Load config for ports
config = configparser.ConfigParser(interpolation=None)
config.read(SETTINGS_PATH)
ZMQ_KEY_PORT = config['Network'].get('zmq_key_port', '5554')

class LauncherWindow(QMainWindow):
    def __init__(self, cfg: RadarConfig, default_ip: str):
        super().__init__()
        self.cfg = cfg
        self.windows = [] # Keep references to prevent GC

        self.setWindowTitle("Craton Vision")
        self.setFixedSize(440, 560)
        self.setWindowIcon(QIcon(ICON_PATH))

        self._apply_style()
        self._build_ui(default_ip)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {BG_BASE};
                font-family: '{FONT}';
            }}
            QLabel#Title {{
                font-size: 28px;
                font-weight: 800;
                color: {TEXT_PRI};
                letter-spacing: -0.5px;
            }}
            QLabel#Subtitle {{
                font-size: 13px;
                color: {TEXT_SEC};
                font-weight: 500;
            }}
            QLabel#SectionHeader {{
                font-size: 11px;
                font-weight: 700;
                color: {TEXT_SEC};
                letter-spacing: 1px;
                text-transform: uppercase;
                margin-top: 10px;
            }}
            QFrame#Card {{
                background: {BG_SURF};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            QLineEdit {{
                background: {BG_BASE};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 10px 12px;
                color: {TEXT_PRI};
                font-size: 14px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {PRIMARY};
            }}
            QPushButton#Action {{
                background: {BG_SURF};
                border: 1px solid {BORDER};
                border-radius: 8px;
                color: {TEXT_PRI};
                font-size: 14px;
                font-weight: 600;
                padding: 14px;
                text-align: left;
            }}
            QPushButton#Action:hover {{
                background: {BG_BASE};
                border-color: {TEXT_SEC};
            }}
            QPushButton#Action:pressed {{
                background: {BORDER};
            }}
            QPushButton#Ghost {{
                background: transparent;
                border: 1px solid {BORDER};
                border-radius: 6px;
                color: {TEXT_SEC};
                font-size: 12px;
                font-weight: 600;
                padding: 8px 12px;
            }}
            QPushButton#Ghost:hover {{
                background: {BORDER};
                color: {TEXT_PRI};
            }}
        """)

    def _build_ui(self, default_ip: str):
        root = QWidget()
        self.setCentralWidget(root)
        main_lay = QVBoxLayout(root)
        main_lay.setContentsMargins(30, 40, 30, 30)
        main_lay.setSpacing(0)

        # ── HEADER ──
        header = QVBoxLayout()
        header.setSpacing(4)
        
        ttl = QLabel("Craton Vision")
        ttl.setObjectName("Title")
        
        sub = QLabel("Multi-Modal Perception Suite")
        sub.setObjectName("Subtitle")
        
        header.addWidget(ttl)
        header.addWidget(sub)
        main_lay.addLayout(header)
        main_lay.addSpacing(35)

        # ── CONNECTION SECTION ──
        conn_lbl = QLabel("Connection Settings")
        conn_lbl.setObjectName("SectionHeader")
        main_lay.addWidget(conn_lbl)
        main_lay.addSpacing(10)

        conn_card = QFrame()
        conn_card.setObjectName("Card")
        conn_lay = QVBoxLayout(conn_card)
        conn_lay.setContentsMargins(16, 16, 16, 16)
        conn_lay.setSpacing(12)

        ip_input_lay = QHBoxLayout()
        ip_input_lay.setSpacing(8)
        
        self.ip_input = QLineEdit()
        self.ip_input.setText(default_ip)
        self.ip_input.setPlaceholderText("Enter Sensor IP (e.g. 192.168.1.50)")
        
        self.btn_test = QPushButton("Test")
        self.btn_test.setObjectName("Ghost")
        self.btn_test.clicked.connect(self._test_connection)
        
        ip_input_lay.addWidget(self.ip_input, stretch=1)
        ip_input_lay.addWidget(self.btn_test)
        conn_lay.addLayout(ip_input_lay)

        self.status_lbl = QLabel("Ready to connect")
        self.status_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 500;")
        conn_lay.addWidget(self.status_lbl)

        main_lay.addWidget(conn_card)
        main_lay.addSpacing(30)

        # ── STREAMS SECTION ──
        stream_lbl = QLabel("Available Streams")
        stream_lbl.setObjectName("SectionHeader")
        main_lay.addWidget(stream_lbl)
        main_lay.addSpacing(10)

        streams_lay = QVBoxLayout()
        streams_lay.setSpacing(10)

        self.btn_radar = QPushButton(" Launch mmWave Radar")
        self.btn_radar.setObjectName("Action")
        self.btn_radar.setIcon(QIcon(ICON_PATH)) # TODO: Use specific icons
        self.btn_radar.clicked.connect(self._launch_radar)

        self.btn_rgb = QPushButton(" Launch RGB Camera")
        self.btn_rgb.setObjectName("Action")
        self.btn_rgb.clicked.connect(self._launch_rgb)

        self.btn_depth = QPushButton(" Launch Depth Map")
        self.btn_depth.setObjectName("Action")
        self.btn_depth.clicked.connect(self._launch_depth)

        streams_lay.addWidget(self.btn_radar)
        streams_lay.addWidget(self.btn_rgb)
        streams_lay.addWidget(self.btn_depth)
        main_lay.addLayout(streams_lay)

        main_lay.addStretch()

        footer = QLabel("v2.1 · Secure CurveZMQ Handshake")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"font-size: 10px; color: {TEXT_SEC}; font-weight: 500;")
        main_lay.addWidget(footer)

    def _test_connection(self):
        ip = self.ip_input.text().strip()
        if not ip:
            self._on_test_result(False, "Please enter an IP address")
            return

        self.status_lbl.setText("Testing handshake...")
        self.status_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
        self.btn_test.setEnabled(False)
        
        self.key_worker = ZmqKeyWorker(ip, ZMQ_KEY_PORT)
        self.key_worker.result.connect(self._on_test_result)
        self.key_worker.start()

    def _on_test_result(self, success: bool, message: str):
        self.btn_test.setEnabled(True)
        self.status_lbl.setText(message)
        if success:
            self.status_lbl.setStyleSheet(f"color: {C_GREEN}; font-size: 11px; font-weight: 600;")
        else:
            self.status_lbl.setStyleSheet("color: #D32F2F; font-size: 11px; font-weight: 600;")

    def _launch_radar(self):
        ip = self.ip_input.text().strip()
        w = RadarStreamWindow(self.cfg, ip)
        w.show()
        self.windows.append(w)

    def _launch_rgb(self):
        ip = self.ip_input.text().strip()
        w = RGBStreamWindow(ip)
        w.show()
        self.windows.append(w)

    def _launch_depth(self):
        ip = self.ip_input.text().strip()
        w = DepthStreamWindow(ip)
        w.show()
        self.windows.append(w)

    def closeEvent(self, event):
        for w in self.windows:
            w.close()
        event.accept()
