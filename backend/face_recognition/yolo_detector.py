import urllib.request
import numpy as np
import cv2
import logging
from ultralytics import YOLO
from backend import config

logger = logging.getLogger("faceai.yolo")

yolo_face_model = None
yolo_object_model = None

def ensure_yolo_face_model_downloaded() -> None:
    """Ensure YOLOv8 face model is downloaded in data folder."""
    if not config.YOLO_FACE_MODEL_FILE.exists():
        logger.info(f"YOLOv8 face model not found. Downloading to {config.YOLO_FACE_MODEL_FILE}...")
        url = "https://github.com/lindevs/yolov8-face/releases/latest/download/yolov8n-face-lindevs.pt"
        try:
            # Create data folder if missing
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(config.YOLO_FACE_MODEL_FILE))
            logger.info("YOLOv8 face model downloaded successfully.")
        except Exception as e:
            logger.error(f"Error downloading YOLOv8 face model: {e}")
            raise RuntimeError(f"Could not download YOLOv8 model: {e}")

def ensure_yolo_object_model_downloaded() -> None:
    """Ensure standard YOLOv8n model is downloaded for object detection."""
    model_path = config.DATA_DIR / "yolov8n.pt"
    if not model_path.exists():
        logger.info(f"YOLOv8n object model not found. Downloading to {model_path}...")
        url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(model_path))
            logger.info("YOLOv8n object model downloaded successfully.")
        except Exception as e:
            logger.error(f"Error downloading YOLOv8n object model: {e}")

def load_yolo_models() -> None:
    """Load the YOLOv8 face model and standard object model into memory."""
    global yolo_face_model, yolo_object_model
    
    if yolo_face_model is None:
        ensure_yolo_face_model_downloaded()
        try:
            yolo_face_model = YOLO(str(config.YOLO_FACE_MODEL_FILE))
            logger.info("YOLOv8 face model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 face model: {e}")
            raise
            
    if yolo_object_model is None:
        ensure_yolo_object_model_downloaded()
        try:
            yolo_object_model = YOLO(str(config.DATA_DIR / "yolov8n.pt"))
            logger.info("YOLOv8 object model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 object model: {e}")
            raise

def get_yolo_face_model() -> YOLO:
    """Get or load YOLO face model."""
    global yolo_face_model
    if yolo_face_model is None:
        load_yolo_models()
    return yolo_face_model

def get_yolo_object_model() -> YOLO:
    """Get or load YOLO object model."""
    global yolo_object_model
    if yolo_object_model is None:
        load_yolo_models()
    return yolo_object_model

def detect_single_face(img: np.ndarray, conf: float = 0.4) -> tuple[tuple[int, int, int, int], list] | None:
    """
    Detect the largest face in the image and retrieve its keypoints.
    Returns:
        ((x, y, w, h), keypoints): tuple containing bounding box and keypoint coordinates or None.
    """
    model = get_yolo_face_model()
    if img is None:
        return None
        
    results = model.predict(img, conf=conf, verbose=False)
    if not results or len(results[0].boxes) == 0:
        return None
        
    boxes = results[0].boxes
    largest_box = None
    largest_idx = -1
    largest_area = 0
    
    # Iterate to find the largest face area
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        w, h = x2 - x1, y2 - y1
        area = w * h
        if area > largest_area:
            largest_area = area
            largest_box = (x1, y1, w, h)
            largest_idx = i
            
    if largest_idx == -1:
        return None
        
    # Get keypoints if available
    keypoints_list = []
    try:
        if hasattr(results[0], 'keypoints') and results[0].keypoints is not None:
            # Shape of xy is [num_boxes, num_keypoints, 2]
            xy = results[0].keypoints.xy.cpu().numpy()
            if len(xy) > largest_idx:
                keypoints_list = xy[largest_idx].tolist()
    except Exception as e:
        logger.warning(f"Failed to retrieve keypoints: {e}")
        
    return largest_box, keypoints_list

def classify_pose(keypoints: list) -> str:
    """
    Classify face pose based on 5 landmarks:
    Keypoint 0: Left Eye
    Keypoint 1: Right Eye
    Keypoint 2: Nose
    Keypoint 3: Left Mouth Corner
    Keypoint 4: Right Mouth Corner
    
    Returns:
        str: 'front', 'left', 'right', 'up', 'down', or 'unknown'
    """
    if not keypoints or len(keypoints) < 5:
        return "unknown"
        
    # Extract coordinates
    # Note: On-screen, Left Eye of user is keypoint 0 (right side of screen usually)
    # and Right Eye of user is keypoint 1 (left side of screen)
    le_x, le_y = keypoints[0]
    re_x, re_y = keypoints[1]
    n_x, n_y = keypoints[2]
    lm_x, lm_y = keypoints[3]
    rm_x, rm_y = keypoints[4]
    
    # Check for empty keypoints (0, 0)
    if le_x == 0 or re_x == 0 or n_x == 0:
        return "unknown"
        
    # Calculate horizontal symmetry
    # Distance from nose to left eye (user's perspective)
    d_left = abs(n_x - le_x)
    # Distance from nose to right eye (user's perspective)
    d_right = abs(n_x - re_x)
    
    ratio = d_left / (d_right + 1e-6)
    
    # Calculate vertical symmetry
    eye_y_avg = (le_y + re_y) / 2.0
    mouth_y_avg = (lm_y + rm_y) / 2.0
    face_h = mouth_y_avg - eye_y_avg
    
    if face_h <= 0:
        face_h = 1.0
        
    v_ratio = (n_y - eye_y_avg) / face_h
    
    # Classification thresholds (robust layout with fallback to front)
    if ratio > 1.6:
        return "right"  # Head turned right (nose closer to right eye)
    elif ratio < 0.6:
        return "left"  # Head turned left (nose closer to left eye)
        
    if v_ratio < 0.38:
        return "up"  # Looking up
    elif v_ratio > 0.62:
        return "down"  # Looking down
        
    return "front"  # Default fallback if not turned left/right/up/down

def detect_objects(img: np.ndarray, conf: float = 0.45) -> list:
    """
    Detect objects in the image (like animals or weapons).
    Returns a list of dicts with 'class_id', 'class_name', 'conf', 'box'.
    """
    model = get_yolo_object_model()
    if img is None:
        return []
        
    results = model.predict(img, conf=conf, verbose=False)
    if not results or len(results[0].boxes) == 0:
        return []
        
    detections = []
    for box in results[0].boxes:
        if box.conf is None:
            continue
        c = float(box.conf[0])
        cls_id = int(box.cls[0])
        cls_name = model.names.get(cls_id, "unknown").lower()
        
        # box.xyxy[0] is [x1, y1, x2, y2]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        detections.append({
            "class_id": cls_id,
            "class_name": cls_name,
            "conf": c,
            "box": (x1, y1, x2, y2)
        })
        
    return detections
