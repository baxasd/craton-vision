import logging
import pyrealsense2 as rs
import numpy as np

# Hook into our standard logging system
log = logging.getLogger("RealSense")

class RealSenseCamera:
    """
    Hardware driver for the Intel RealSense Depth Camera.
    Handles stream configuration, frame alignment (matching 2D RGB to 3D Depth),
    and hardware-accelerated post-processing filters.
    """
    def __init__(self, width=640, height=480, fps=30, auto_exposure=True, manual_exposure=156,
                 preset=4, spatial=True, temporal=True, hole_filling=True):
        self.pipeline = None
        self.use_spatial = spatial
        self.use_temporal = temporal
        self.use_hole_filling = hole_filling
        
        try:
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            # Request specific streams from the hardware
            self.config.enable_stream(rs.stream.color, width, height, rs.format.rgb8, fps)
            self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            
            # Start the camera and grab the active profile
            self.profile = self.pipeline.start(self.config)

            # ── HARDWARE PRESET ──
            self.set_preset(preset)
            
            # Mathematically warp the Depth map so it perfectly matches the RGB image
            self.align = rs.align(rs.stream.color)
            
            # ── HARDWARE FILTERS (Optimal Intel Pipeline) ──
            self.depth_to_disparity = rs.disparity_transform(True)
            self.spatial_filter = rs.spatial_filter()
            self.temporal_filter = rs.temporal_filter()
            self.disparity_to_depth = rs.disparity_transform(False)
            
            self.hole_filling_filter = rs.hole_filling_filter()
            
            # ── EXPOSURE CONTROL ──
            self.set_exposure(auto_exposure, manual_exposure)
            
            log.info(f"RealSense started successfully at {width}x{height} @ {fps} FPS")
            
        except Exception as e:
            log.error(f"Camera hardware initialization failed: {e}")
            self.pipeline = None

    def set_preset(self, preset: int):
        """Changes the onboard visual preset (e.g. 4 = High Density)."""
        if not self.profile: return
        try:
            depth_sensor = self.profile.get_device().first_depth_sensor()
            if depth_sensor.supports(rs.option.visual_preset):
                depth_sensor.set_option(rs.option.visual_preset, preset) 
                log.info(f"Depth Sensor set to preset: {preset}")
        except Exception as e:
            log.warning(f"Could not set hardware preset: {e}")

    def set_exposure(self, auto_exposure: bool, manual_exposure: int):
        """Dives into the physical camera sensors to configure lighting."""
        if not self.profile: return
        
        device = self.profile.get_device()
        for sensor in device.query_sensors():
            # We only want to change the exposure of the Color camera, not the Infrared laser
            if sensor.is_color_sensor():
                if auto_exposure:
                    sensor.set_option(rs.option.enable_auto_exposure, 1)
                else:
                    sensor.set_option(rs.option.enable_auto_exposure, 0)
                    sensor.set_option(rs.option.exposure, manual_exposure)

    def get_frames(self):
        """Pulls the newest frame from the USB buffer, applies optimal DSP filters, and aligns it."""
        if not self.pipeline: 
            return None, None
            
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            
            # Align first to guarantee perfect 1:1 mapping with the RGB frame
            aligned = self.align.process(frames)
            
            color_frame = aligned.get_color_frame()
            depth_frame = aligned.get_depth_frame()
            
            if not color_frame or not depth_frame: 
                return None, None
            
            # Apply Software Filters (Post-Alignment) based on toggle states
            if self.use_spatial or self.use_temporal:
                depth_frame = self.depth_to_disparity.process(depth_frame)
                if self.use_spatial:
                    depth_frame = self.spatial_filter.process(depth_frame)
                if self.use_temporal:
                    depth_frame = self.temporal_filter.process(depth_frame)
                depth_frame = self.disparity_to_depth.process(depth_frame)
                
            if self.use_hole_filling:
                depth_frame = self.hole_filling_filter.process(depth_frame)
            
            return np.asanyarray(color_frame.get_data()), depth_frame
            
        except Exception as e:
            log.debug(f"Frame dropped or timeout: {e}")
            return None, None

    def stop(self):
        """Safely releases the USB port so other applications can use the camera."""
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                log.error(f"Error while stopping RealSense pipeline: {e}")