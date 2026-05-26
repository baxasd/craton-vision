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
