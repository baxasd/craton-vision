import logging
import pyrealsense2 as rs
import numpy as np

# Hook into our standard logging system
log = logging.getLogger("RealSense")

class RealSenseCamera:
    """
    Hardware driver for the Intel RealSense Depth Camera.
    Handles stream configuration, frame alignment, and hardware-accelerated filters.
    """
    def __init__(self, width=640, height=480, fps=30, auto_exposure=True, manual_exposure=156,
                 preset=4, spatial=False, temporal=False, hole_filling=False, decimation=False):
        self.pipeline = None
        self.use_spatial = spatial
        self.use_temporal = temporal
        self.use_hole_filling = hole_filling
        self.use_decimation = decimation
        
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
            
            # ── HARDWARE FILTERS ──
            self.decimation_filter = rs.decimation_filter()
            self.spatial_filter = rs.spatial_filter()
            self.temporal_filter = rs.temporal_filter()
            self.hole_filling_filter = rs.hole_filling_filter()
            
            # ── SENSOR CONTROL ──
            self.set_exposure(auto_exposure, manual_exposure)
            self.set_laser_power(150) # Default healthy laser power
            
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

    def set_laser_power(self, power: int):
        """Controls the IR projector power (0 to 360). Higher power = better texture for depth."""
        if not self.profile: return
        try:
            depth_sensor = self.profile.get_device().first_depth_sensor()
            if depth_sensor.supports(rs.option.laser_power):
                depth_sensor.set_option(rs.option.laser_power, float(power))
        except Exception as e:
            log.warning(f"Could not set laser power: {e}")

    def set_exposure(self, auto_exposure: bool, manual_exposure: int):
        """Configures exposure for both Color and Infrared sensors."""
        if not self.profile: return
        
        device = self.profile.get_device()
        for sensor in device.query_sensors():
            # Apply to both Color and Depth/IR sensors
            if sensor.supports(rs.option.enable_auto_exposure):
                sensor.set_option(rs.option.enable_auto_exposure, 1 if auto_exposure else 0)
            
            if not auto_exposure and sensor.supports(rs.option.exposure):
                # Scale exposure for IR if needed, but here we use the same base
                sensor.set_option(rs.option.exposure, float(manual_exposure))

    def get_frames(self):
        """Pulls frames, aligns them, and applies filters."""
        if not self.pipeline: 
            return None, None
            
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            
            # Align first to guarantee perfect 1:1 mapping with the RGB frame
            aligned_frames = self.align.process(frames)
            
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()
            
            if not color_frame or not depth_frame: 
                return None, None
            
            # Apply Software Filters to the aligned depth
            if self.use_spatial:
                depth_frame = self.spatial_filter.process(depth_frame)
            if self.use_temporal:
                depth_frame = self.temporal_filter.process(depth_frame)
            if self.use_hole_filling:
                depth_frame = self.hole_filling_filter.process(depth_frame)

            return np.asanyarray(color_frame.get_data()), depth_frame
            
        except Exception as e:
            log.debug(f"Frame processing error: {e}")
            return None, None

    def stop(self):
        """Safely releases the USB port."""
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                log.error(f"Error while stopping RealSense pipeline: {e}")
