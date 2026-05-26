import cv2
import time
import numpy as np
import configparser
from core.camera import RealSenseCamera
from core.pose import PoseEstimator
from core.config import SETTINGS_PATH, ensure_config

def noop(*args):
    pass

def main():
    # Ensure config exists
    ensure_config()
    
    config = configparser.ConfigParser()
    config.read(SETTINGS_PATH)
    
    width = config.getint('Camera', 'width', fallback=640)
    height = config.getint('Camera', 'height', fallback=480)
    fps = config.getint('Camera', 'fps', fallback=30)
    auto_exp = config.getboolean('Camera', 'auto_exposure', fallback=True)
    exposure = config.getint('Camera', 'exposure', fallback=156)
    preset = config.getint('Camera', 'preset', fallback=4)
    spatial = config.getboolean('Camera', 'spatial_filter', fallback=True)
    temporal = config.getboolean('Camera', 'temporal_filter', fallback=True)
    hole_fill = config.getboolean('Camera', 'hole_filling', fallback=True)

    mp_complex = config.getint('MediaPipe', 'model_complexity', fallback=1)
    mp_conf = config.getfloat('MediaPipe', 'min_confidence', fallback=0.5)

    print("Initializing RealSense camera...")
    camera = RealSenseCamera(
        width=width, height=height, fps=fps, 
        auto_exposure=auto_exp, manual_exposure=exposure,
        preset=preset, spatial=spatial, temporal=temporal, hole_filling=hole_fill
    )
    
    if not camera.pipeline:
        print("Failed to start RealSense camera.")
        return

    pose_estimator = PoseEstimator(model_complexity=mp_complex, min_conf=mp_conf)

    window_name = "RealSense Calibration (Press 's' to Save, 'q' to Quit)"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    # Trackbars for realtime configuration
    cv2.createTrackbar("Preset(0-5)", window_name, preset, 5, noop)
    cv2.createTrackbar("Auto Exp", window_name, 1 if auto_exp else 0, 1, noop)
    cv2.createTrackbar("Exposure", window_name, exposure, 5000, noop)
    cv2.createTrackbar("Spatial", window_name, 1 if spatial else 0, 1, noop)
    cv2.createTrackbar("Temporal", window_name, 1 if temporal else 0, 1, noop)
    cv2.createTrackbar("Hole Fill", window_name, 1 if hole_fill else 0, 1, noop)

    print("\nStarting realtime calibration stream...")
    print("- MediaPipe joints will render as green circles on the RGB feed.")
    print("- Depth map is rendered using a heatmap on the right.")
    print("- Press 's' to save the current trackbar settings to settings.ini.")
    print("- Press 'q' to quit.")

    prev_time = time.time()
    
    try:
        while True:
            # Read current trackbar states
            cur_preset = cv2.getTrackbarPos("Preset(0-5)", window_name)
            cur_auto = cv2.getTrackbarPos("Auto Exp", window_name) == 1
            cur_exp = cv2.getTrackbarPos("Exposure", window_name)
            cur_spatial = cv2.getTrackbarPos("Spatial", window_name) == 1
            cur_temporal = cv2.getTrackbarPos("Temporal", window_name) == 1
            cur_hole = cv2.getTrackbarPos("Hole Fill", window_name) == 1

            # Apply settings to hardware dynamically if they changed
            if cur_preset != preset:
                preset = cur_preset
                camera.set_preset(preset)
            
            if cur_auto != auto_exp or cur_exp != exposure:
                auto_exp = cur_auto
                exposure = max(1, cur_exp) # avoid 0 exposure
                camera.set_exposure(auto_exp, exposure)

            # Update filter toggles in the camera class loop
            camera.use_spatial = cur_spatial
            camera.use_temporal = cur_temporal
            camera.use_hole_filling = cur_hole

            color_frame, depth_frame = camera.get_frames()
            if color_frame is None or depth_frame is None:
                continue
                
            # FPS Calculation
            curr_time = time.time()
            fps_display = 1 / (curr_time - prev_time)
            prev_time = curr_time

            # Color conversion for OpenCV display (Camera outputs RGB natively, OpenCV requires BGR)
            disp_color = cv2.cvtColor(color_frame, cv2.COLOR_RGB2BGR)

            # Inference (MediaPipe expects RGB)
            pose_3d = pose_estimator.estimate(color_frame)

            # Overlay Skeleton Joints
            if pose_3d:
                for i, (x, y, z) in enumerate(pose_3d):
                    cv2.circle(disp_color, (int(x), int(y)), 4, (0, 255, 0), -1)
                    
            # Process depth frame into a color heatmap for visual inspection
            if hasattr(depth_frame, 'get_data'):
                depth_data = np.asanyarray(depth_frame.get_data())
                # Normalize depth scaling for display (scales millimeter distance to 0-255)
                depth_norm = cv2.convertScaleAbs(depth_data, alpha=0.03)
                disp_depth = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
            else:
                disp_depth = np.zeros_like(disp_color)

            # Draw labels
            cv2.putText(disp_color, f"RGB + MediaPipe | FPS: {fps_display:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(disp_depth, "Filtered Depth Map", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Concatenate side by side for comparison
            combined = np.hstack((disp_color, disp_depth))
            cv2.imshow(window_name, combined)

            # Keyboard Input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Persist to settings.ini
                config['Camera']['preset'] = str(preset)
                config['Camera']['auto_exposure'] = str(auto_exp)
                config['Camera']['exposure'] = str(exposure)
                config['Camera']['spatial_filter'] = str(cur_spatial)
                config['Camera']['temporal_filter'] = str(cur_temporal)
                config['Camera']['hole_filling'] = str(cur_hole)
                with open(SETTINGS_PATH, 'w') as f:
                    config.write(f)
                print(">> Hardware Settings saved to settings.ini!")

    except KeyboardInterrupt:
        pass
    finally:
        print("Stopping camera stream...")
        camera.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
