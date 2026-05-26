import logging
import mediapipe as mp

# Hook into our standard logging system
log = logging.getLogger("PoseEstimator")

class PoseEstimator:
    """
    Mediapipe Pose Estimator.
    """
    def __init__(self, model_complexity=1, min_conf=0.5, target_size=None):
        self.mp_pose = mp.solutions.pose
        
        # Initialize the heavy AI model in memory
        self.pose = self.mp_pose.Pose(
            static_image_mode=False, # False = Video mode (uses tracking across frames for speed)
            model_complexity=model_complexity,
            min_detection_confidence=min_conf,
            min_tracking_confidence=min_conf
        )

    def estimate(self, image):
        """
        Takes a raw camera frame and returns a list of (x, y, z) tuples in image pixels.
        Returns None if no human body is detected.
        """
        try:
            # Inference (Feed it to the Neural Network)
            results = self.pose.process(image)
            if not results.pose_landmarks:
                return None

            h, w = image.shape[:2]
            restored = []
            for lm in results.pose_landmarks.landmark:
                # MediaPipe returns normalized coordinates (0.0 to 1.0)
                x = lm.x * w
                y = lm.y * h
                # Z is relative to the hips and at roughly the same scale as X
                z = lm.z * w
                restored.append((x, y, z))
                
            return restored

        except Exception as e:
            log.error(f"MediaPipe inference failed: {e}")
            return None