import sys
import os
import logging
import configparser
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon

from src.radar.parse import RadarConfig
from src.utils.theme import SETTINGS_PATH, ICON_PATH
from src.utils.config import ensure_config
from src.viewer.launcher import LauncherWindow
from src.viewer.components import FONT

ensure_config(SETTINGS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("Launcher")

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

config = configparser.ConfigParser(interpolation=None)
config.read(SETTINGS_PATH)
HW_CFG_FILE = config['Hardware']['radar_cfg_file']
DEFAULT_IP  = config['Viewer']['default_ip']

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    
    font = QFont(FONT)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    try:
        cfg = RadarConfig(HW_CFG_FILE)
        window = LauncherWindow(cfg, DEFAULT_IP)
        window.show()
        app.exec()
    except Exception as e:
        log.error(e)

if __name__ == "__main__":
    main()
