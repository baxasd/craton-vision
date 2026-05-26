# Headless Camera Recorder

A lightweight, headless CLI tool for capturing 3D human pose estimation using an Intel RealSense camera and MediaPipe. 

![Python](https://img.shields.io/badge/python-3.11-green)

---

## 🏛️ Architecture

The project has been aggressively stripped down to focus exclusively on headless camera capture:

```
core/
├── camera.py  (Intel RealSense driver & frame alignment)
├── pose.py    (MediaPipe Pose Estimator & 2D inference)
├── depth.py   (3D deprojection math)
└── config.py  (Settings generation & loading)
app.py         (Minimal CLI menu)
```

---

## 🚀 Quick Start

1. Connect your Intel RealSense camera.
2. Run the application:
   ```bash
   python app.py
   ```
3. A `settings.ini` file will be auto-generated if it does not exist. You can configure camera width, height, fps, and exposure here.
4. Follow the minimal CLI menu to specify an output JSONL file and a duration (in seconds, 0 for infinite).

---

## ⚙️ Supported Hardware

**Intel RealSense (e.g. D435i)**
RGB-Depth camera for precise skeletal kinematics and joint angle calculation.