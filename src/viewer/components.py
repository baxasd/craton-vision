import os
import re
import zmq
import logging
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QSizePolicy, QFrame, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QPixmap

from src.utils.theme import (
    ROOT_DIR, COLOR_LEFT, COLOR_RIGHT, COLOR_CENTER, COLOR_CLEAN_DATA,
    SETTINGS_PATH, ICON_PATH
)

log = logging.getLogger("Viewer.Components")

# ── Design tokens ─────────────────────────────────────────────────────────────

def _load_st_theme():
    st_theme = {
        "primaryColor": "#BF0000",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F3F4F5",
        "textColor": "#242024"
    }
    try:
        with open(os.path.join(ROOT_DIR, ".streamlit", "config.toml"), "r") as f:
            content = f.read()
            for k in st_theme.keys():
                match = re.search(fr'{k}\s*=\s*"([^"]+)"', content)
                if match:
                    st_theme[k] = match.group(1)
    except Exception:
        pass
    return st_theme

st_config = _load_st_theme()

C_LEFT    = COLOR_LEFT
C_RIGHT   = COLOR_RIGHT
C_CENTER  = COLOR_CENTER
C_GREEN   = COLOR_CLEAN_DATA

BG_BASE   = st_config["secondaryBackgroundColor"]
BG_SURF   = st_config["backgroundColor"]
BG_PANEL  = st_config["backgroundColor"]
BG_HDR    = st_config["secondaryBackgroundColor"]
BORDER    = "#E2E2E2"

TEXT_PRI  = st_config["textColor"]
TEXT_SEC  = "#605E5C"
TEXT_MUT  = "#A19F9D"
PRIMARY   = st_config["primaryColor"]

FONT      = "Inter"

# ── Network helper ────────────────────────────────────────────────────────────

def fetch_public_key(ip: str, port: str, timeout_ms: int = 3000):
    ctx  = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0) # Don't hang on close
    sock.connect(f"tcp://{ip}:{port}")
    
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    
    try:
        sock.send_string("REQ_KEY", flags=zmq.NOBLOCK)
        socks = dict(poller.poll(timeout_ms))
        
        if sock in socks and socks[sock] == zmq.POLLIN:
            key = sock.recv(flags=zmq.NOBLOCK)
            log.info(f"TOFU: key received from {ip}")
            return key
        else:
            log.error(f"TOFU: timeout or no response from {ip}:{port}")
            return None
    except Exception as e:
        log.error(f"TOFU error: {e}")
        return None
    finally:
        sock.close()
        ctx.term()

# ── UI components ─────────────────────────────────────────────────────────────

class FillLabel(QWidget):
    """Contain-mode image display — preserves aspect ratio without zooming or stretching."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._lbl    = QLabel(self)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet("background: transparent; border: none;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background: {BG_BASE};")

    def set_pixmap(self, px: QPixmap):
        self._pixmap = px
        self._repaint()

    def _repaint(self):
        if self._pixmap is None or not self.width() or not self.height():
            return
        w, h   = self.width(), self.height()
        scaled = self._pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._lbl.setPixmap(scaled)
        lx = (w - scaled.width()) // 2
        ly = (h - scaled.height()) // 2
        self._lbl.setGeometry(lx, ly, scaled.width(), scaled.height())

    def resizeEvent(self, e):
        self._repaint()

class Panel(QFrame):
    """MD3 surface-container card with a clean header bar."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setStyleSheet(f"""
            QFrame#Panel {{
                background: {BG_SURF};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(34)
        hdr.setStyleSheet(f"""
            background: {BG_HDR};
            border-bottom: 1px solid {BORDER};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0)
        hl.setSpacing(8)

        ttl = QLabel(title.upper())
        ttl.setStyleSheet(f"""
            color: {TEXT_SEC};
            font-family: '{FONT}';
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)
        hl.addWidget(ttl)
        hl.addStretch()

        outer.addWidget(hdr)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(0)
        outer.addLayout(self._body)

    def body(self) -> QVBoxLayout:
        return self._body
