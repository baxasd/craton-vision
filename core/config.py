import configparser
from pathlib import Path

SETTINGS_PATH = "settings.ini"

def ensure_config():
    """Generates a default settings.ini if it doesn't exist."""
    if not Path(SETTINGS_PATH).exists():
        config = configparser.ConfigParser()
        
        # Camera-specific settings
        config['Camera'] = {
            'width': '640',
            'height': '480',
            'fps': '30',
            'auto_exposure': 'True',
            'exposure': '156',
            'laser_power': '150',
            'preset': '4',
            'spatial_filter': 'False',
            'temporal_filter': 'False',
            'hole_filling': 'False'
        }
        
        # MediaPipe-specific settings
        config['MediaPipe'] = {
            'model_complexity': '1',
            'min_confidence': '0.5',
            'target_size': '512'
        }
        
        with open(SETTINGS_PATH, 'w') as f:
            config.write(f)
