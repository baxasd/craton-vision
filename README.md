# Craton Vision


[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/) 
[![Intel RealSense](https://img.shields.io/badge/PyRealsense-2.58+-0071C5.svg?style=flat&logo=intel&logoColor=white)](https://github.com/IntelRealSense/librealsense)
[![MediaPipe](https://img.shields.io/badge/Mediapipe-0.10.21-00C0FF.svg?style=flat&logo=google&logoColor=white)](https://mediapipe.dev/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blueviolet.svg?style=flat)](LICENSE)

A headless CLI tool for 3D human pose estimation and recording using an Intel RealSense depth camera and MediaPipe. 

## Architecture

The system is designed for minimal overhead and consists of core modules and a main application node:

- **`core/camera.py`**: Manages Intel RealSense pipeline, alignment, and hardware filters.
- **`core/pose.py`**: Handles MediaPipe Pose estimation and 2D coordinate extraction.
- **`core/depth.py`**: Performs 3D deprojection math for pixel-to-point translation.
- **`core/config.py`**: Auto-generates and manages `settings.ini`.
- **`app.py`**: CLI interface and high-speed binary serialization.

## Binary File Structure

Records are saved in a compact `.bin` format optimized for throughput:

1. **Header**: 
   - `4 bytes (uint)`: Length of metadata JSON.
   - `N bytes`: Metadata string (UTF-8 JSON).
2. **Frame Block** (Repeated):
   - `8 bytes (double)`: Unix Timestamp.
   - `4 bytes (uint)`: Number of detected joints ($J$).
   - **Joint Data** ($J$ entries):
     - `4 bytes (uint)`: Joint ID.
     - `12 bytes (3x float)`: 3D coordinates ($x, y, z$).
     - `8 bytes (2x int)`: 2D pixel coordinates ($px, py$).

## Installation & Usage

### Setup
1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Execution
Run the application to start the CLI menu:
```bash
python app.py
```
A `settings.ini` file will be generated on first run. Configure resolution, FPS, and filters there.

To visually configure the camera, run
```bash
python calibrator.py
```

To inspect captured data, run
```bash
python viewer.py
```

To build executable

```bash
pyinstaller --clean tools/camera_recorder.spec
```

## Contribution & License

- **License**: Distributed under the [Apache 2.0 License](LICENSE).
- **Contributions**: Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. PRs containing unreviewed, generated AI content will be closed.
