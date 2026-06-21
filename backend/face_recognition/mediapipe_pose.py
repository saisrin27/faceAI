import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pathlib import Path
import logging

logger = logging.getLogger("faceai.mediapipe_pose")

# Model path
MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "mediapipe" / "face_landmarker.task"

# Global detector instance
_landmarker = None

def init_landmarker() -> None:
    """Initialize the MediaPipe Face Landmarker client."""
    global _landmarker
    if _landmarker is not None:
        return
        
    try:
        # Download task model if not exists
        if not MODEL_PATH.exists():
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            import urllib.request
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            logger.info(f"Downloading FaceLandmarker task from {url}...")
            urllib.request.urlretrieve(url, str(MODEL_PATH))
            logger.info("FaceLandmarker downloaded successfully.")
            
        base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )
        _landmarker = vision.FaceLandmarker.create_from_options(options)
        logger.info("MediaPipe FaceLandmarker task initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MediaPipe FaceLandmarker: {e}")
        raise

def get_landmarker() -> vision.FaceLandmarker:
    """Get the active landmarker instance."""
    global _landmarker
    if _landmarker is None:
        init_landmarker()
    return _landmarker

def get_face_bbox(landmarks, img_w: int, img_h: int) -> tuple[int, int, int, int]:
    """Calculate pixel bounding box with padding around all landmarks."""
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    x = int(x_min * img_w)
    y = int(y_min * img_h)
    w = int((x_max - x_min) * img_w)
    h = int((y_max - y_min) * img_h)
    
    # Add 15% margin around the face
    margin_w = int(w * 0.15)
    margin_h = int(h * 0.15)
    
    x_out = max(0, x - margin_w)
    y_out = max(0, y - margin_h)
    w_out = min(img_w - x_out, w + 2 * margin_w)
    h_out = min(img_h - y_out, h + 2 * margin_h)
    
    return x_out, y_out, w_out, h_out

def classify_pose_from_landmarks(landmarks) -> str:
    """
    Classify facial pose from 3D FaceMesh landmarks using ratio-based symmetry.
    Uses robust landmarks averages:
      - Left eye average of outer (33) and inner (133)
      - Right eye average of outer (263) and inner (362)
      - Nose tip (1)
      - Mouth corners (61, 291)
    """
    le_x = (landmarks[33].x + landmarks[133].x) / 2.0
    le_y = (landmarks[33].y + landmarks[133].y) / 2.0
    
    re_x = (landmarks[263].x + landmarks[362].x) / 2.0
    re_y = (landmarks[263].y + landmarks[362].y) / 2.0
    
    n_x, n_y = landmarks[1].x, landmarks[1].y
    lm_x, lm_y = landmarks[61].x, landmarks[61].y
    rm_x, rm_y = landmarks[291].x, landmarks[291].y
    
    # Horizontal symmetry
    d_left = abs(n_x - le_x)
    d_right = abs(n_x - re_x)
    ratio = d_left / (d_right + 1e-6)
    
    # Vertical symmetry
    eye_y_avg = (le_y + re_y) / 2.0
    mouth_y_avg = (lm_y + rm_y) / 2.0
    face_h = mouth_y_avg - eye_y_avg
    if face_h <= 0:
        face_h = 1.0
        
    v_ratio = (n_y - eye_y_avg) / face_h
    
    # Check rotation thresholds
    if ratio > 1.35:
        return "right"
    elif ratio < 0.70:
        return "left"
        
    if v_ratio < 0.40:
        return "up"
    elif v_ratio > 0.58:
        return "down"
        
    return "front"

def detect_single_face_pose(img: np.ndarray) -> tuple[tuple[int, int, int, int], str] | None:
    """
    Detect face and classify its pose.
    Returns:
        ((x, y, w, h), pose_str) or None if no face is detected.
    """
    if img is None:
        return None
        
    try:
        landmarker = get_landmarker()
        img_h, img_w = img.shape[:2]
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        result = landmarker.detect(mp_image)
        if not result.face_landmarks or len(result.face_landmarks) == 0:
            return None
            
        landmarks = result.face_landmarks[0]
        bbox = get_face_bbox(landmarks, img_w, img_h)
        pose_str = classify_pose_from_landmarks(landmarks)
        
        return bbox, pose_str
    except Exception as e:
        logger.error(f"Error in MediaPipe pose detection: {e}")
        return None
