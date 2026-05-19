import zmq
import logging
import numpy as np
import scipy.ndimage as ndimage
import configparser
from PyQt6.QtCore import QThread, pyqtSignal
from src.radar.parse import RadarConfig
from src.utils.theme import SETTINGS_PATH
from src.viewer.components import fetch_public_key

log = logging.getLogger("Viewer.Workers")

# Load config for worker constants
config = configparser.ConfigParser(interpolation=None)
config.read(SETTINGS_PATH)

ZMQ_RADAR_PORT = config['Network'].get('zmq_radar_port', '5555')
ZMQ_CAM_PORT   = config['Network'].get('zmq_camera_port', '5556')
ZMQ_KEY_PORT   = config['Network'].get('zmq_key_port', '5554')

MAX_RANGE      = float(config['Viewer']['max_range_m'])
DISP_LOW_PCT   = float(config['Viewer']['low_pct'])
DISP_HIGH_PCT  = float(config['Viewer']['high_pct'])

CLIENT_PUBLIC  = config['Security']['client_public'].encode('ascii')
CLIENT_SECRET  = config['Security']['client_secret'].encode('ascii')

class ZmqKeyWorker(QThread):
    result = pyqtSignal(bool, str) # success, message

    def __init__(self, ip: str, port: str):
        super().__init__()
        self.ip   = ip
        self.port = port

    def run(self):
        try:
            key = fetch_public_key(self.ip, self.port)
            if key:
                self.result.emit(True, "Connection Successful")
            else:
                self.result.emit(False, "Handshake Failed - Check Network")
        except Exception as e:
            self.result.emit(False, f"Error: {str(e)}")

class ZmqRadarWorker(QThread):
    new_frame = pyqtSignal(np.ndarray, float, float)
    error     = pyqtSignal(str)

    def __init__(self, cfg: RadarConfig, ip: str, zoom_y: float, zoom_x: float):
        super().__init__()
        self.cfg      = cfg
        self.ip       = ip
        self.running  = True
        self.zoom_y   = zoom_y
        self.zoom_x   = zoom_x
        self.max_bin  = min(int(MAX_RANGE / cfg.rangeRes), cfg.numRangeBins)
        self._n_range = cfg.numRangeBins
        self._n_vel   = cfg.numLoops
        self._expected = self._n_range * self._n_vel
        self.ctx    = zmq.Context()
        self.socket = None

    def run(self):
        try:
            srv = fetch_public_key(self.ip, ZMQ_KEY_PORT)
            if srv is None:
                raise ConnectionError(f"No public key from {self.ip}")

            self.socket = self.ctx.socket(zmq.SUB)
            self.socket.curve_secretkey = CLIENT_SECRET
            self.socket.curve_publickey = CLIENT_PUBLIC
            self.socket.curve_serverkey = srv
            self.socket.connect(f"tcp://{self.ip}:{ZMQ_RADAR_PORT}")
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        except Exception as e:
            self.error.emit(str(e))
            return

        while self.running:
            try:
                if self.socket.poll(100) == 0:
                    continue
                msg = self.socket.recv(flags=zmq.NOBLOCK)
                raw = np.frombuffer(msg, dtype=np.uint16)
                if raw.size != self._expected:
                    continue
                rd      = raw.astype(np.float32).reshape(self._n_range, self._n_vel)
                rd      = rd[:self.max_bin, :]
                display = 20.0 * np.log10(np.abs(np.fft.fftshift(rd, axes=1)) + 1e-6)
                smooth  = ndimage.zoom(display, (self.zoom_y, self.zoom_x), order=1)
                lo      = float(np.percentile(smooth, DISP_LOW_PCT))
                hi      = float(np.percentile(smooth, DISP_HIGH_PCT))
                if lo >= hi:
                    hi = lo + 0.1
                self.new_frame.emit(smooth, lo, hi)
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.wait()
        if self.socket:
            self.socket.close()
        self.ctx.term()

class ZmqCameraWorker(QThread):
    new_frame = pyqtSignal(dict, bytes, bytes)
    error     = pyqtSignal(str)

    def __init__(self, ip: str):
        super().__init__()
        self.ip      = ip
        self.running = True
        self.ctx     = zmq.Context()
        self.socket  = None

    def run(self):
        try:
            srv = fetch_public_key(self.ip, ZMQ_KEY_PORT)
            if srv is None:
                raise ConnectionError(f"No public key from {self.ip}")

            self.socket = self.ctx.socket(zmq.SUB)
            self.socket.curve_secretkey = CLIENT_SECRET
            self.socket.curve_publickey = CLIENT_PUBLIC
            self.socket.curve_serverkey = srv
            self.socket.connect(f"tcp://{self.ip}:{ZMQ_CAM_PORT}")
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        except Exception as e:
            self.error.emit(str(e))
            return

        while self.running:
            try:
                if self.socket.poll(100) == 0:
                    continue
                parts = self.socket.recv_multipart(flags=zmq.NOBLOCK)
                if len(parts) >= 2:
                    meta        = json.loads(parts[0].decode('utf-8'))
                    img_bytes   = parts[1]
                    depth_bytes = parts[2] if len(parts) == 3 else b''
                    self.new_frame.emit(meta, img_bytes, depth_bytes)
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self.running = False
        self.wait()
        if self.socket:
            self.socket.close()
        self.ctx.term()
