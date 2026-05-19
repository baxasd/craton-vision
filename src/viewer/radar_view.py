import numpy as np
import pyqtgraph as pg
import configparser
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtGui import QIcon, QFont
from src.radar.parse import RadarConfig
from src.utils.theme import ICON_PATH, SETTINGS_PATH
from src.viewer.components import (
    BG_BASE, BG_SURF, TEXT_SEC, BORDER, FONT, Panel
)
from src.viewer.workers import ZmqRadarWorker

# Load config for radar view constants
config = configparser.ConfigParser(interpolation=None)
config.read(SETTINGS_PATH)

MAX_RANGE   = float(config['Viewer']['max_range_m'])
CMAP        = config['Viewer']['cmap']
SMOOTH_GRID = int(config['Viewer']['smooth_grid_size'])

class RadarStreamWindow(QMainWindow):
    def __init__(self, cfg: RadarConfig, ip: str):
        super().__init__()
        self.cfg           = cfg
        self.publisher_ip  = ip
        self.zoom_y        = 1.0
        self.zoom_x        = 1.0
        self.max_range_val = min(int(MAX_RANGE / cfg.rangeRes), cfg.numRangeBins) * cfg.rangeRes
        self.dop_max       = cfg.dopMax

        self.setWindowTitle(f"Radar Stream  ·  {ip}")
        self.resize(800, 600)
        self.setWindowIcon(QIcon(ICON_PATH))

        self._precompute_zoom()
        self._apply_style()
        self._build_ui()
        self._start_worker()

    def _precompute_zoom(self):
        rows = min(int(MAX_RANGE / self.cfg.rangeRes), self.cfg.numRangeBins)
        cols = self.cfg.numLoops
        self.zoom_y = max(SMOOTH_GRID, rows) / rows
        self.zoom_x = max(SMOOTH_GRID, cols) / cols

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

        panel = Panel("mmWave Radar")
        self.plot_radar = self._make_radar_plot()
        panel.body().addWidget(self.plot_radar)
        
        lay.addWidget(panel)

    def _make_radar_plot(self) -> pg.PlotWidget:
        pg.setConfigOptions(imageAxisOrder="row-major", antialias=True)
        plot = pg.PlotWidget()
        plot.setBackground(BG_SURF)
        
        ax_style = {'color': TEXT_SEC, 'font-size': '10px', 'font-family': FONT}
        plot.setLabel("left",   "Range",    units="m",   **ax_style)
        plot.setLabel("bottom", "Velocity", units="m/s", **ax_style)
        
        for axis in ('left', 'bottom'):
            ax = plot.getAxis(axis)
            ax.setPen(pg.mkPen(color=BORDER, width=1))
            ax.setTextPen(pg.mkPen(color=TEXT_SEC))
            ax.setTickFont(QFont(FONT, 8))

        plot.showGrid(x=True, y=True, alpha=0.1)
        plot.setXRange(-self.dop_max, self.dop_max, padding=0)
        plot.setYRange(0, self.max_range_val, padding=0)

        self.img_radar = pg.ImageItem()
        self.img_radar.setColorMap(pg.colormap.get(CMAP))
        plot.addItem(self.img_radar)
        return plot

    def _start_worker(self):
        self.worker = ZmqRadarWorker(self.cfg, self.publisher_ip, self.zoom_y, self.zoom_x)
        self.worker.new_frame.connect(self._on_frame)
        self.worker.start()

    def _on_frame(self, smooth: np.ndarray, lo: float, hi: float):
        self.img_radar.setImage(smooth, autoLevels=False, levels=(lo, hi))
        self.img_radar.setRect(
            pg.QtCore.QRectF(-self.dop_max, 0, self.dop_max * 2.0, self.max_range_val))

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()
