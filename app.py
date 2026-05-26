import time
import json
import struct
import logging
import configparser
from pathlib import Path

from core.camera import RealSenseCamera
from core.pose import PoseEstimator
from core.depth import get_mean_depth, deproject_pixel_to_point
from core.config import ensure_config, SETTINGS_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("HeadlessCapture")

def run_capture(output_file, duration):
    # Load settings from settings.ini
    config = configparser.ConfigParser()
    config.read(SETTINGS_PATH)
    
    width = config.getint('Camera', 'width', fallback=640)
    height = config.getint('Camera', 'height', fallback=480)
    fps = config.getint('Camera', 'fps', fallback=30)
    auto_exposure = config.getboolean('Camera', 'auto_exposure', fallback=True)
    exposure = config.getint('Camera', 'exposure', fallback=156)
    preset = config.getint('Camera', 'preset', fallback=4)
    spatial = config.getboolean('Camera', 'spatial_filter', fallback=True)
    temporal = config.getboolean('Camera', 'temporal_filter', fallback=True)
    hole_fill = config.getboolean('Camera', 'hole_filling', fallback=True)

    mp_complex = config.getint('MediaPipe', 'model_complexity', fallback=1)
    mp_conf = config.getfloat('MediaPipe', 'min_confidence', fallback=0.5)
    mp_size = config.getint('MediaPipe', 'target_size', fallback=512)

    camera = RealSenseCamera(
        width=width, 
        height=height, 
        fps=fps, 
        auto_exposure=auto_exposure, 
        manual_exposure=exposure,
        preset=preset,
        spatial=spatial,
        temporal=temporal,
        hole_filling=hole_fill
    )
    
    if not camera.pipeline:
        log.error("Failed to initialize RealSense camera. Returning to menu.")
        return

    pose_estimator = PoseEstimator(model_complexity=mp_complex, min_conf=mp_conf, target_size=mp_size)

    log.info(f"Starting binary capture to {output_file}...")
    log.info("Press Ctrl+C to stop manually.")
    
    output_path = Path(output_file)
    start_time = time.time()
    frame_count = 0
    
    try:
        depth_intrin = None
        # Open in binary append/write mode 'wb'
        with open(output_path, "wb") as f:
            
            # Write metadata header
            metadata = {
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "camera": {
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "auto_exposure": auto_exposure,
                    "exposure": exposure,
                    "preset": preset,
                    "spatial_filter": spatial,
                    "temporal_filter": temporal,
                    "hole_filling": hole_fill
                },
                "mediapipe": {
                    "model_complexity": mp_complex,
                    "min_confidence": mp_conf,
                    "target_size": mp_size
                }
            }
            meta_json = json.dumps(metadata).encode('utf-8')
            # Pack string length (unsigned int) and then the string itself
            f.write(struct.pack("I", len(meta_json)))
            f.write(meta_json)
            
            while True:
                if duration > 0 and (time.time() - start_time) > duration:
                    log.info(f"Capture duration of {duration}s reached.")
                    break
                    
                color_frame, depth_frame = camera.get_frames()
                
                if color_frame is None or depth_frame is None:
                    continue

                if not depth_frame.is_depth_frame():
                    continue
                depth_frame = depth_frame.as_depth_frame()

                if depth_intrin is None:
                    depth_profile = depth_frame.get_profile().as_video_stream_profile()
                    depth_intrin = depth_profile.get_intrinsics()

                pose_2d = pose_estimator.estimate(color_frame)
                
                if pose_2d:
                    joints_3d = {}
                    h, w = color_frame.shape[:2]
                    
                    for i, (x, y, z) in enumerate(pose_2d):
                        px, py = int(x), int(y)
                        
                        d = get_mean_depth(depth_frame, px, py, w, h, patch=2)
                        
                        if d is not None:
                            pt_3d = deproject_pixel_to_point(depth_intrin, px, py, d)
                            if pt_3d:
                                joints_3d[i] = {
                                    'x': pt_3d[0], 'y': pt_3d[1], 'z': pt_3d[2],
                                    'px': px, 'py': py
                                }
                    
                    if joints_3d:
                        # 1. Write Timestamp (double: 8 bytes) and Number of Joints (unsigned int: 4 bytes)
                        header = struct.pack("dI", time.time(), len(joints_3d))
                        f.write(header)
                        
                        # 2. Write each joint: ID(I), x(f), y(f), z(f), px(i), py(i) -> 24 bytes per joint
                        for j_id, data in joints_3d.items():
                            joint_bytes = struct.pack(
                                "Ifffii", 
                                j_id, data['x'], data['y'], data['z'], data['px'], data['py']
                            )
                            f.write(joint_bytes)
                            
                        # Force flush to disk to ensure streaming safety
                        f.flush()
                        
                frame_count += 1
                if frame_count % fps == 0:
                    log.info(f"Processed {frame_count} frames...")
                    
    except KeyboardInterrupt:
        log.info("Capture interrupted by user.")
    except Exception as e:
        log.error(f"Error during capture: {e}")
    finally:
        camera.stop()
        log.info(f"Capture stopped. Total frames processed: {frame_count}")


def main():
    # Make sure the config file exists on startup
    ensure_config()
    
    while True:
        print("\n--- Camera Recorder ---")
        print("1. Start Capture")
        print("2. Quit")
        
        try:
            choice = input("Select an option [1-2]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
            
        if choice == "1":
            default_file = f"{time.strftime('%Y%m%d_%H%M%S')}.bin"
            out_file = input(f"Output file [{default_file}]: ").strip() or default_file
            duration_str = input("Duration in seconds (0 for infinite) [0]: ").strip() or "0"
            
            try:
                duration = int(duration_str)
            except ValueError:
                print("Invalid duration. Please enter an integer.")
                continue
                
            run_capture(out_file, duration)
            
        elif choice == "2":
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    main()
