import cv2
import time
import numpy as np
import configparser
import dearpygui.dearpygui as dpg
from core.camera import RealSenseCamera
from core.pose import PoseEstimator
from core.config import SETTINGS_PATH, ensure_config

def save_settings():
    config = configparser.ConfigParser()
    config.read(SETTINGS_PATH)
    config['Camera']['preset'] = str(dpg.get_value("preset"))
    config['Camera']['auto_exposure'] = str(dpg.get_value("auto_exp"))
    config['Camera']['exposure'] = str(dpg.get_value("exposure"))
    config['Camera']['laser_power'] = str(dpg.get_value("laser"))
    config['Camera']['spatial_filter'] = str(dpg.get_value("spatial"))
    config['Camera']['spatial_alpha'] = str(dpg.get_value("spatial_alpha"))
    config['Camera']['spatial_delta'] = str(dpg.get_value("spatial_delta"))
    config['Camera']['spatial_iterations'] = str(dpg.get_value("spatial_iterations"))
    config['Camera']['temporal_filter'] = str(dpg.get_value("temporal"))
    config['Camera']['temporal_alpha'] = str(dpg.get_value("temporal_alpha"))
    config['Camera']['temporal_delta'] = str(dpg.get_value("temporal_delta"))
    config['Camera']['temporal_persistence'] = str(dpg.get_value("temporal_persistence"))
    config['Camera']['hole_filling'] = str(dpg.get_value("hole_fill"))
    config['Camera']['hole_filling_mode'] = str(dpg.get_value("hole_filling_mode"))
    with open(SETTINGS_PATH, 'w') as f:
        config.write(f)
    print(">> Settings saved to settings.ini!")

def main():
    ensure_config()
    
    config = configparser.ConfigParser()
    config.read(SETTINGS_PATH)
    
    # Load settings with defaults
    cam_cfg = config['Camera'] if 'Camera' in config else {}
    width = int(cam_cfg.get('width', '640'))
    height = int(cam_cfg.get('height', '480'))
    fps = int(cam_cfg.get('fps', '30'))
    
    init_auto_exp = cam_cfg.get('auto_exposure', 'False') == 'True'
    init_exposure = int(cam_cfg.get('exposure', '156'))
    init_laser = int(cam_cfg.get('laser_power', '150'))
    init_preset = cam_cfg.get('preset', 'High Density') # String for combobox
    
    init_decimation = cam_cfg.get('decimation_filter', 'False') == 'True'
    init_decimation_magnitude = int(cam_cfg.get('decimation_magnitude', '2'))
    
    init_disparity = cam_cfg.get('disparity_filter', 'False') == 'True'

    init_spatial = cam_cfg.get('spatial_filter', 'False') == 'True'
    init_spatial_alpha = float(cam_cfg.get('spatial_alpha', '0.5'))
    init_spatial_delta = int(cam_cfg.get('spatial_delta', '20'))
    init_spatial_iterations = int(cam_cfg.get('spatial_iterations', '2'))

    init_temporal = cam_cfg.get('temporal_filter', 'False') == 'True'
    init_temporal_alpha = float(cam_cfg.get('temporal_alpha', '0.4'))
    init_temporal_delta = int(cam_cfg.get('temporal_delta', '20'))
    init_temporal_persistence = int(cam_cfg.get('temporal_persistence', '3'))

    init_hole_fill = cam_cfg.get('hole_filling', 'False') == 'True'
    init_hole_filling_mode = int(cam_cfg.get('hole_filling_mode', '1'))

    mp_cfg = config['MediaPipe'] if 'MediaPipe' in config else {}
    pose_estimator = PoseEstimator(
        model_complexity=int(mp_cfg.get('model_complexity', '1')), 
        min_conf=float(mp_cfg.get('min_confidence', '0.5'))
    )

    print("Initializing RealSense camera (Filters off by default)...")
    camera = RealSenseCamera(
        width=width, height=height, fps=fps, 
        auto_exposure=init_auto_exp, manual_exposure=init_exposure,
        preset=init_preset, spatial=init_spatial, temporal=init_temporal, 
        hole_filling=init_hole_fill, decimation=init_decimation, disparity=init_disparity
    )
    camera.set_laser_power(init_laser)
    
    # Apply initial filter configurations
    camera.decimation_magnitude = init_decimation_magnitude
    
    camera.spatial_alpha = init_spatial_alpha
    camera.spatial_delta = init_spatial_delta
    camera.spatial_iterations = init_spatial_iterations
    
    camera.temporal_alpha = init_temporal_alpha
    camera.temporal_delta = init_temporal_delta
    camera.temporal_persistence = init_temporal_persistence
    
    camera.hole_filling_mode = init_hole_filling_mode
    
    if not camera.pipeline:
        print("Failed to start RealSense camera.")
        return

    # --- DearPyGui Setup ---
    dpg.create_context()
    
    # The texture size is two frames side-by-side (RGB + Depth)
    tex_width, tex_height = width * 2, height
    
    with dpg.texture_registry(show=False):
        # Create a dynamic texture initialized with zeros (RGBA float32 flat array)
        empty_data = np.zeros((tex_width * tex_height * 4,), dtype=np.float32)
        dpg.add_dynamic_texture(width=tex_width, height=tex_height, default_value=empty_data, tag="video_texture")

    preset_items = ["Custom", "Default", "Hand", "High Accuracy", "High Density", "Medium Density"]

    with dpg.window(tag="Primary Window"):
        # Top: Video Feed mapping to the texture
        dpg.add_image("video_texture")
        
        # Bottom: Native UI Controls
        with dpg.child_window(height=350): # Increased height to fit all controls
            with dpg.group(horizontal=True):
                # Column 1: Hardware & Exposure
                with dpg.group(width=300):
                    dpg.add_text("HARDWARE SETTINGS", color=(100, 200, 255))
                    dpg.add_combo(label="Visual Preset", items=preset_items, default_value=init_preset, tag="preset")
                    dpg.add_slider_int(label="Laser Power", default_value=init_laser, min_value=0, max_value=360, tag="laser")
                    
                    dpg.add_spacer(height=10)
                    dpg.add_text("EXPOSURE", color=(100, 200, 255))
                    dpg.add_checkbox(label="Auto Exposure", default_value=init_auto_exp, tag="auto_exp")
                    dpg.add_slider_int(label="Manual Exposure", default_value=init_exposure, min_value=1, max_value=5000, tag="exposure")

                    dpg.add_spacer(height=10)
                    dpg.add_text("FPS: 0.0", tag="fps_text", color=(255, 255, 0))
                    
                    dpg.add_spacer(height=10)
                    dpg.add_button(label="Save Settings", callback=save_settings, width=-1)

                # Column 2: Spatial & Temporal Filters
                with dpg.group(width=300):
                    dpg.add_text("SPATIAL FILTER", color=(100, 200, 255))
                    dpg.add_checkbox(label="Enable Spatial", default_value=init_spatial, tag="spatial")
                    dpg.add_slider_float(label="Smooth Alpha", default_value=init_spatial_alpha, min_value=0.25, max_value=1.0, tag="spatial_alpha")
                    dpg.add_slider_int(label="Smooth Delta", default_value=init_spatial_delta, min_value=1, max_value=50, tag="spatial_delta")
                    dpg.add_slider_int(label="Hole Fill (Iterations)", default_value=init_spatial_iterations, min_value=0, max_value=5, tag="spatial_iterations")
                    
                    dpg.add_spacer(height=10)
                    dpg.add_text("TEMPORAL FILTER", color=(100, 200, 255))
                    dpg.add_checkbox(label="Enable Temporal", default_value=init_temporal, tag="temporal")
                    dpg.add_slider_float(label="Filter Alpha", default_value=init_temporal_alpha, min_value=0.0, max_value=1.0, tag="temporal_alpha")
                    dpg.add_slider_int(label="Filter Delta", default_value=init_temporal_delta, min_value=1, max_value=100, tag="temporal_delta")
                    dpg.add_slider_int(label="Persistence Index", default_value=init_temporal_persistence, min_value=0, max_value=8, tag="temporal_persistence")

                # Column 3: Decimation, Disparity, Hole Filling
                with dpg.group(width=300):
                    dpg.add_text("PRE-PROCESSING", color=(100, 200, 255))
                    dpg.add_checkbox(label="Decimation Filter", default_value=init_decimation, tag="decimation")
                    dpg.add_slider_int(label="Decimation Mag", default_value=init_decimation_magnitude, min_value=2, max_value=8, tag="decimation_magnitude")
                    dpg.add_checkbox(label="Depth <-> Disparity (Recommended)", default_value=init_disparity, tag="disparity")
                    
                    dpg.add_spacer(height=10)
                    dpg.add_text("HOLE FILLING", color=(100, 200, 255))
                    dpg.add_checkbox(label="Enable Hole Filling", default_value=init_hole_fill, tag="hole_fill")
                    dpg.add_slider_int(label="Mode", default_value=init_hole_filling_mode, min_value=0, max_value=2, tag="hole_filling_mode")
                    dpg.add_text("0: fill_from_left", color=(150, 150, 150))
                    dpg.add_text("1: farest_from_around", color=(150, 150, 150))
                    dpg.add_text("2: nearest_from_around", color=(150, 150, 150))

    dpg.create_viewport(title='RealSense Calibrator', width=tex_width + 50, height=tex_height + 400, resizable=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)

    prev_time = time.time()
    
    last_preset = init_preset
    last_auto_exp = init_auto_exp
    last_exposure = init_exposure
    last_laser = init_laser

    try:
        while dpg.is_dearpygui_running():
            # 1. Read Current UI States
            curr_preset = dpg.get_value("preset")
            curr_auto_exp = dpg.get_value("auto_exp")
            curr_exposure = dpg.get_value("exposure")
            curr_laser = dpg.get_value("laser")
            
            # Hide/Show manual exposure slider based on Auto Exposure
            dpg.configure_item("exposure", show=not curr_auto_exp)
            
            # 2. Update Hardware if UI states changed
            if curr_preset != last_preset:
                camera.set_preset(curr_preset)
                last_preset = curr_preset
            
            if curr_auto_exp != last_auto_exp or curr_exposure != last_exposure:
                camera.set_exposure(curr_auto_exp, max(1, curr_exposure))
                last_auto_exp = curr_auto_exp
                last_exposure = curr_exposure
                
            if curr_laser != last_laser:
                camera.set_laser_power(curr_laser)
                last_laser = curr_laser

            # 3. Apply software filters per frame
            camera.use_decimation = dpg.get_value("decimation")
            camera.decimation_magnitude = dpg.get_value("decimation_magnitude")
            camera.use_disparity = dpg.get_value("disparity")
            
            camera.use_spatial = dpg.get_value("spatial")
            camera.spatial_alpha = dpg.get_value("spatial_alpha")
            camera.spatial_delta = dpg.get_value("spatial_delta")
            camera.spatial_iterations = dpg.get_value("spatial_iterations")
            
            camera.use_temporal = dpg.get_value("temporal")
            camera.temporal_alpha = dpg.get_value("temporal_alpha")
            camera.temporal_delta = dpg.get_value("temporal_delta")
            camera.temporal_persistence = dpg.get_value("temporal_persistence")
            
            camera.use_hole_filling = dpg.get_value("hole_fill")
            camera.hole_filling_mode = dpg.get_value("hole_filling_mode")


            # 4. Fetch and Process Frames
            color_frame, depth_frame = camera.get_frames()
            if color_frame is not None and depth_frame is not None:
                curr_time = time.time()
                fps_display = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
                prev_time = curr_time
                
                # Update FPS in the control zone
                dpg.set_value("fps_text", f"FPS: {fps_display:.1f}")

                pose_3d = pose_estimator.estimate(color_frame)
                disp_color = cv2.cvtColor(color_frame, cv2.COLOR_RGB2BGR)
                
                if pose_3d:
                    for i, (x, y, z) in enumerate(pose_3d):
                        cv2.circle(disp_color, (int(x), int(y)), 4, (0, 255, 0), -1)

                if hasattr(depth_frame, 'get_data'):
                    depth_data = np.asanyarray(depth_frame.get_data())
                    depth_norm = cv2.convertScaleAbs(depth_data, alpha=0.03)
                    disp_depth = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
                else:
                    disp_depth = np.zeros_like(disp_color)

                # Ensure dimensions match before stacking (decimation changes depth shape)
                if disp_depth.shape[:2] != disp_color.shape[:2]:
                    disp_depth = cv2.resize(disp_depth, (disp_color.shape[1], disp_color.shape[0]))

                # Combine images side by side (Text Overlays removed)
                combined = np.hstack((disp_color, disp_depth))
                
                # Convert to RGBA (DearPyGui expects RGBA)
                rgba = cv2.cvtColor(combined, cv2.COLOR_BGR2RGBA)
                
                # Ensure the frame strictly matches the texture size to avoid crashes
                if rgba.shape[1] != tex_width or rgba.shape[0] != tex_height:
                    rgba = cv2.resize(rgba, (tex_width, tex_height))

                # Normalize array to 0.0 - 1.0 float32, then flatten it rapidly
                texture_data = (rgba.astype(np.float32) / 255.0).ravel()
                
                # Feed the raw float data into the DearPyGui texture
                dpg.set_value("video_texture", texture_data)

            # 5. Render GUI Loop
            dpg.render_dearpygui_frame()

    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        dpg.destroy_context()

if __name__ == "__main__":
    main()
