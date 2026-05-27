import sys
import os

# Import mediapipe as early as possible to avoid DLL issues
try:
    import mediapipe
except ImportError:
    pass
