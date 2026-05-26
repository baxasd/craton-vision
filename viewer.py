import math
import time
import json
import struct
import dearpygui.dearpygui as dpg

# Standard MediaPipe Pose connections for skeleton drawing
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26),
    (25, 27), (26, 28),
    (27, 29), (28, 30),
    (29, 31), (30, 32), (27, 31), (28, 32)
]

# Global application state
app_state = {
    'filepath': '',
    'metadata': {},
    'frames': [],
    'current_frame': 0,
    'is_playing': False,
    'last_time': 0.0,
    'fps_target': 30.0
}

def load_bin_file(filepath):
    frames = []
    metadata = {}
    
    try:
        with open(filepath, 'rb') as f:
            # Read metadata length
            len_buf = f.read(4)
            if not len_buf:
                return metadata, frames
            
            meta_len = struct.unpack("I", len_buf)[0]
            
            # Read metadata JSON
            meta_bytes = f.read(meta_len)
            metadata = json.loads(meta_bytes.decode('utf-8'))
            
            # Read frames sequentially
            while True:
                header_buf = f.read(12) # double (8 bytes) + unsigned int (4 bytes)
                if not header_buf or len(header_buf) < 12:
                    break
                    
                ts, num_joints = struct.unpack("dI", header_buf)
                
                joints = {}
                # Read each joint (24 bytes)
                for _ in range(num_joints):
                    j_buf = f.read(24) # Ifffii
                    if len(j_buf) < 24:
                        break
                    j_id, x, y, z, px, py = struct.unpack("Ifffii", j_buf)
                    joints[j_id] = {'x': x, 'y': y, 'z': z}
                
                frames.append({'ts': ts, 'joints': joints})
                
    except Exception as e:
        print(f"Error loading file: {e}")
        
    return metadata, frames


def project_3d_to_2d(x, y, z, canvas_w, canvas_h, yaw, pitch, radius, cx, cy, cz):
    """Simple 3D to 2D perspective projection."""
    # 1. Translate to origin/center
    x -= cx
    y -= cy
    z -= cz
    
    # 2. Rotate Y (Yaw)
    x_rot_y = x * math.cos(yaw) - z * math.sin(yaw)
    z_rot_y = x * math.sin(yaw) + z * math.cos(yaw)
    
    # 3. Rotate X (Pitch)
    y_rot_x = y * math.cos(pitch) - z_rot_y * math.sin(pitch)
    z_rot_x = y * math.sin(pitch) + z_rot_y * math.cos(pitch)
    
    # 4. Apply camera radius (Z-translation)
    z_cam = z_rot_x + radius
    
    # Avoid rendering points behind the camera
    if z_cam < 0.1:
        return None
        
    # 5. Perspective projection
    fov = 500.0 # Scaling factor for the canvas
    px = (x_rot_y / z_cam) * fov + (canvas_w / 2)
    py = (y_rot_x / z_cam) * fov + (canvas_h / 2)
    
    return px, py


def render_current_frame():
    """Reads state, projects 3D coordinates, and draws to the DPG canvas."""
    if not app_state['frames']:
        return
        
    dpg.delete_item("canvas", children_only=True)
    
    frame_idx = app_state['current_frame']
    if frame_idx >= len(app_state['frames']):
        frame_idx = len(app_state['frames']) - 1
        
    joints = app_state['frames'][frame_idx]['joints']
    
    yaw = dpg.get_value("yaw")
    pitch = dpg.get_value("pitch")
    radius = dpg.get_value("radius")
    cx = dpg.get_value("center_x")
    cy = dpg.get_value("center_y")
    cz = dpg.get_value("center_z")
    
    w = 640
    h = 480
    
    projected = {}
    
    # Project all valid joints
    for j_id, p in joints.items():
        res = project_3d_to_2d(p['x'], p['y'], p['z'], w, h, yaw, pitch, radius, cx, cy, cz)
        if res:
            projected[j_id] = res
            dpg.draw_circle(center=res, radius=3, color=(0, 255, 0, 255), fill=(0, 255, 0, 100), parent="canvas")
            
    # Draw skeleton connections
    for c_start, c_end in POSE_CONNECTIONS:
        if c_start in projected and c_end in projected:
            p1 = projected[c_start]
            p2 = projected[c_end]
            dpg.draw_line(p1=p1, p2=p2, color=(255, 255, 255, 150), thickness=2, parent="canvas")


def file_dialog_callback(sender, app_data):
    filepath = app_data['file_path_name']
    print(f"Loading {filepath}...")
    
    meta, frames = load_bin_file(filepath)
    if not frames:
        print("File is empty or corrupted.")
        return
        
    app_state['filepath'] = filepath
    app_state['metadata'] = meta
    app_state['frames'] = frames
    app_state['current_frame'] = 0
    app_state['is_playing'] = False
    
    # Update UI bounds and texts
    dpg.configure_item("frame_slider", max_value=len(frames)-1)
    dpg.set_value("frame_slider", 0)
    
    # Format metadata for the text block
    meta_str = json.dumps(meta, indent=2)
    dpg.set_value("meta_text", f"Loaded File: {filepath}\nFrames: {len(frames)}\n\nMetadata:\n{meta_str}")
    
    # Center camera on the mean of the first frame's points
    j0 = frames[0]['joints']
    if j0:
        mean_x = sum(p['x'] for p in j0.values()) / len(j0)
        mean_y = sum(p['y'] for p in j0.values()) / len(j0)
        mean_z = sum(p['z'] for p in j0.values()) / len(j0)
        dpg.set_value("center_x", mean_x)
        dpg.set_value("center_y", mean_y)
        dpg.set_value("center_z", mean_z)
        
    render_current_frame()


def toggle_play():
    app_state['is_playing'] = not app_state['is_playing']
    dpg.set_item_label("play_btn", "Pause" if app_state['is_playing'] else "Play")
    app_state['last_time'] = time.time()


def slider_changed():
    app_state['current_frame'] = dpg.get_value("frame_slider")
    render_current_frame()


def main():
    dpg.create_context()
    
    with dpg.file_dialog(directory_selector=False, show=False, callback=file_dialog_callback, tag="file_dialog_id", width=600, height=400):
        dpg.add_file_extension(".bin", color=(0, 255, 0, 255))
        dpg.add_file_extension(".*")

    with dpg.window(tag="Primary Window"):
        with dpg.group(horizontal=True):
            
            # --- Left Column: Visualizer Canvas ---
            with dpg.child_window(width=640, height=520):
                dpg.add_text("3D VISUALIZER", color=(100, 200, 255))
                # Create a solid black background
                with dpg.drawlist(width=620, height=450):
                    dpg.draw_rectangle(pmin=(0,0), pmax=(640, 480), color=(0,0,0,255), fill=(20,20,25,255))
                    dpg.add_draw_node(tag="canvas")
                
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Play", tag="play_btn", callback=toggle_play, width=70)
                    dpg.add_slider_int(tag="frame_slider", min_value=0, max_value=0, width=545, callback=slider_changed)

            # --- Right Column: Controls & Metadata ---
            with dpg.child_window(width=400, height=520):
                dpg.add_text("FILE CONTROLS", color=(100, 200, 255))
                dpg.add_button(label="Load .bin File", callback=lambda: dpg.show_item("file_dialog_id"), width=-1)
                
                dpg.add_spacer(height=10)
                dpg.add_text("CAMERA ORBIT", color=(100, 200, 255))
                dpg.add_slider_float(label="Yaw", default_value=0.0, min_value=-math.pi, max_value=math.pi, tag="yaw", callback=render_current_frame)
                dpg.add_slider_float(label="Pitch", default_value=0.0, min_value=-math.pi/2, max_value=math.pi/2, tag="pitch", callback=render_current_frame)
                dpg.add_slider_float(label="Distance", default_value=2.0, min_value=0.1, max_value=10.0, tag="radius", callback=render_current_frame)
                
                dpg.add_spacer(height=10)
                dpg.add_text("TARGET OFFSET", color=(100, 200, 255))
                dpg.add_slider_float(label="Offset X", default_value=0.0, min_value=-2.0, max_value=2.0, tag="center_x", callback=render_current_frame)
                dpg.add_slider_float(label="Offset Y", default_value=0.0, min_value=-2.0, max_value=2.0, tag="center_y", callback=render_current_frame)
                dpg.add_slider_float(label="Offset Z", default_value=1.0, min_value=0.0, max_value=5.0, tag="center_z", callback=render_current_frame)
                
                dpg.add_spacer(height=10)
                with dpg.child_window(height=-1):
                    dpg.add_text("METADATA", color=(100, 200, 255))
                    dpg.add_text("No file loaded.\nClick 'Load .bin File' to begin.", tag="meta_text", wrap=360)


    dpg.create_viewport(title='Visualizer', width=1080, height=580, resizable=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)

    while dpg.is_dearpygui_running():
        # Handle playback animation
        if app_state['is_playing'] and app_state['frames']:
            curr_time = time.time()
            if (curr_time - app_state['last_time']) > (1.0 / app_state['fps_target']):
                app_state['current_frame'] += 1
                if app_state['current_frame'] >= len(app_state['frames']):
                    app_state['current_frame'] = 0 # loop
                    
                dpg.set_value("frame_slider", app_state['current_frame'])
                render_current_frame()
                app_state['last_time'] = curr_time
                
        dpg.render_dearpygui_frame()

    dpg.destroy_context()

if __name__ == "__main__":
    main()
