import sys
import configparser
from pathlib import Path
import os

def get_base_path():
    """Returns the base path for the application (where the .exe or project root is)."""
    if getattr(sys, 'frozen', False):
        # Path to the directory containing the executable
        return Path(os.path.dirname(sys.executable))
    else:
        # Path to the project root (two levels up from core/config.py)
        return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_resource_path(relative_path):
    """Get absolute path to bundled resource, works for dev and for PyInstaller."""
    if getattr(sys, 'frozen', False):
        # sys._MEIPASS points to the internal data directory (e.g. 'libs')
        return Path(sys._MEIPASS) / relative_path
    else:
        return get_base_path() / relative_path

SETTINGS_PATH = get_base_path() / "settings.ini"

def ensure_config():
    """Generates a default settings.ini if it doesn't exist."""
    if not SETTINGS_PATH.exists():
        config = configparser.ConfigParser()
        
        # General settings
        config['General'] = {
            'output_dir': 'recordings'
        }
        
        # Camera-specific settings
        config['Camera'] = {
            'width': '640',
            'height': '480',
            'fps': '30',
            'auto_exposure': 'True',
            'exposure': '156',
            'laser_power': '150',
            'preset': 'High Density',
            'decimation_filter': 'False',
            'decimation_magnitude': '2',
            'disparity_filter': 'False',
            'spatial_filter': 'False',
            'spatial_alpha': '0.5',
            'spatial_delta': '20',
            'spatial_iterations': '2',
            'temporal_filter': 'False',
            'temporal_alpha': '0.4',
            'temporal_delta': '20',
            'temporal_persistence': '3',
            'hole_filling': 'False',
            'hole_filling_mode': '1'
        }
        
        # MediaPipe-specific settings
        config['MediaPipe'] = {
            'model_complexity': '1',
            'min_confidence': '0.5',
            'target_size': '512'
        }
        
        with open(SETTINGS_PATH, 'w') as f:
            config.write(f)
