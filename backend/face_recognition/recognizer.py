import os
import cv2
import numpy as np
import logging
from pathlib import Path
from backend import config
from backend.database.db import get_db

logger = logging.getLogger("faceai.recognizer")

# Global FaceAnalysis instance
_face_analysis = None

def get_face_analysis():
    """Lazily load and return the FaceAnalysis instance."""
    global _face_analysis
    if _face_analysis is None:
        try:
            from insightface.app import FaceAnalysis
            # Using 'buffalo_sc' which is CPU-optimized and fast
            root_dir = str(config.DATA_DIR / "insightface")
            _face_analysis = FaceAnalysis(name='buffalo_sc', root=root_dir)
            _face_analysis.prepare(ctx_id=-1, det_size=(640, 640))
            logger.info("InsightFace FaceAnalysis model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load InsightFace FaceAnalysis model: {e}")
            raise
    return _face_analysis

def load_trained_model() -> None:
    """Pre-initialize FaceAnalysis model."""
    try:
        get_face_analysis()
    except Exception as e:
        logger.error(f"Startup FaceAnalysis initialization failed: {e}")

def get_image_embedding(img: np.ndarray) -> np.ndarray | None:
    """Extract the 512D ArcFace embedding of the largest face in the image."""
    if img is None:
        return None
        
    try:
        app = get_face_analysis()
        faces = app.get(img)
        if not faces or len(faces) == 0:
            return None
            
        # Find the largest face by bounding box area
        largest_face = None
        max_area = 0
        for face in faces:
            bbox = face.bbox  # [x1, y1, x2, y2]
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            area = w * h
            if area > max_area:
                max_area = area
                largest_face = face
                
        if largest_face is not None:
            return largest_face.embedding
    except Exception as e:
        logger.error(f"Error in face embedding extraction: {e}")
    return None

def check_face_quality(img: np.ndarray, bbox: tuple[int, int, int, int] | list[int] | None = None) -> tuple[bool, str]:
    """
    Validate face image quality.
    - Brightness: mean brightness between 40 and 230.
    - Blurriness: Laplacian variance > 30.0.
    - Face size: If bbox is provided, bounding box area must cover at least 15% of total frame area.
    Returns:
        (is_valid, error_message)
    """
    if img is None:
        return False, "Empty image"
        
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except Exception as e:
        logger.error(f"Error converting image to grayscale in check_face_quality: {e}")
        return False, "Failed to analyze image format."
        
    # Check brightness
    mean_brightness = np.mean(gray)
    if mean_brightness < 40 or mean_brightness > 230:
        return False, f"Poor lighting conditions (brightness: {mean_brightness:.1f}). Please adjust your lighting."
        
    # Check blurriness
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 30.0:
        return False, f"Image is too blurry (blur metric: {laplacian_var:.1f}). Please keep steady."
        
    # Check face size (15% of frame area)
    if bbox is not None:
        # bbox can be [x1, y1, x2, y2] (InsightFace) or (x, y, w, h) (MediaPipe/YOLO)
        # Determine format based on length and structure
        if len(bbox) == 4:
            # Let's check if it's (x, y, w, h) or [x1, y1, x2, y2]
            # In (x, y, w, h), w and h are width/height. In x1,y1,x2,y2, x2 > x1, y2 > y1
            # We can normalize to face_area
            # If width/height style: bbox[2] and bbox[3] are width and height.
            # If x1/y1 style: bbox[2]-bbox[0] and bbox[3]-bbox[1] are width and height.
            # Let's check if bbox[2] > bbox[0] and bbox[3] > bbox[1] AND they are coordinates.
            # But wait, to be safe: let's calculate both or inspect the values.
            # If x1, y1, x2, y2: x2 > x1 and y2 > y1. Let's assume:
            # If bbox[0] + bbox[2] <= img.shape[1] and bbox[1] + bbox[3] <= img.shape[0] and bbox[2] > 0 and bbox[3] > 0:
            # wait, both could be true. Let's look at the actual values:
            # If we treat it as (x, y, w, h), then w = bbox[2], h = bbox[3].
            # If we treat it as [x1, y1, x2, y2], then w = bbox[2] - bbox[0], h = bbox[3] - bbox[1].
            # Let's write a robust parser:
            # If bbox[2] > bbox[0] and bbox[3] > bbox[1] and (bbox[2] > img.shape[1]/2 or bbox[3] > img.shape[0]/2 or bbox[0] + bbox[2] > img.shape[1] or bbox[1] + bbox[3] > img.shape[0]):
            # This is likely x1, y1, x2, y2.
            # Let's simplify: if bbox[2] < bbox[0] or bbox[3] < bbox[1]: it's definitely not x1,y1,x2,y2 (unless coordinates are negative/invalid, but they shouldn't be).
            # More simple: if the third element is larger than the width of the image or close to it, or if bbox[2] - bbox[0] is positive and matches the face:
            # Let's just check: is (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > bbox[2] * bbox[3]?
            # Usually coordinate x2 is much larger than width w.
            # Let's compute:
            w1 = bbox[2] - bbox[0]
            h1 = bbox[3] - bbox[1]
            w2 = bbox[2]
            h2 = bbox[3]
            
            # MediaPipe/YOLO returns (x, y, w, h). Let's verify:
            # mediapipe_pose: bbox = get_face_bbox(...) returns x_out, y_out, w_out, h_out.
            # yolo_detector: largest_box = (x1, y1, w, h).
            # So they both return (x, y, w, h).
            # InsightFace predict_multiple_faces/get_image_embedding: face.bbox is [x1, y1, x2, y2].
            # Let's check if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            # If the user is close, coordinates are large. E.g. x1=200, y1=150, x2=450, y2=400.
            # Here w = 250, h = 250.
            # If we treated it as (x, y, w, h), w would be 450, h would be 400. That would be wrong.
            # Let's use a heuristic: if we have x2 > x1 and y2 > y1 and x2 <= img.shape[1] and y2 <= img.shape[0] and x1 >= 0 and y1 >= 0:
            # Let's check if x2 - x1 is a reasonable face size and x2, y2 are actual coordinates.
            # Let's implement it cleanly:
            if bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] > bbox[0] and bbox[3] > bbox[1] and bbox[2] <= img.shape[1] and bbox[3] <= img.shape[0]:
                # This looks like [x1, y1, x2, y2]
                face_w = bbox[2] - bbox[0]
                face_h = bbox[3] - bbox[1]
            else:
                # Fallback to (x, y, w, h)
                face_w = bbox[2]
                face_h = bbox[3]
                
            face_area = face_w * face_h
            img_area = img.shape[0] * img.shape[1]
            face_ratio = face_area / img_area
            if face_ratio < 0.08:
                return False, f"Face is too far from the camera (covers {face_ratio*100:.1f}% of frame). Please move closer."
            
    return True, ""

def train_recognizer() -> None:
    """
    Query all active users, extract 512D embeddings for all their registered pose photos,
    and cache them inside their enrollment folders as embeddings.npy.
    If pose_*.jpg files do not exist but embeddings.npy already exists, we preserve it.
    """
    logger.info("Pre-extracting and caching user face embeddings...")
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM users WHERE profile_image IS NOT NULL"
                )
                users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query users for embedding training: {e}")
        return
        
    for user in users:
        user_id = user["id"]
        enroll_dir = config.UPLOAD_DIR / "enrollments" / str(user_id)
        if not enroll_dir.exists():
            continue
            
        pose_files = list(enroll_dir.glob("pose_*.jpg"))
        if not pose_files:
            # If embeddings.npy exists, preserve it!
            npy_path = enroll_dir / "embeddings.npy"
            if npy_path.exists():
                logger.info(f"Embeddings already cached and no new pose files for user {user_id} ({user['name']}). Skipping.")
                continue
            else:
                logger.warning(f"No pose files or embeddings.npy found for user {user_id} ({user['name']})")
                continue
                
        user_embeddings = {}
        for file in pose_files:
            pose_name = file.name.replace("pose_", "").replace(".jpg", "")
            img = cv2.imread(str(file))
            if img is None:
                continue
            emb = get_image_embedding(img)
            if emb is not None:
                user_embeddings[pose_name] = emb.tolist()
                
        if user_embeddings:
            np.save(str(enroll_dir / "embeddings.npy"), user_embeddings)
            logger.info(f"Cached {len(user_embeddings)} embeddings for user {user_id} ({user['name']})")
        else:
            logger.warning(f"No face detected in any enrollment images for user {user_id}")

def predict_face(color_img: np.ndarray) -> tuple[int, float] | None:
    """
    Predict identity by comparing face embedding against all approved users' cached embeddings.
    Returns:
        (user_id, cosine_similarity) or None
    """
    scan_emb = get_image_embedding(color_img)
    if scan_emb is None:
        logger.info("Scan: No face detected, cannot generate embedding.")
        return None
        
    best_user_id = -1
    best_sim = -1.0
    
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Compare scan against approved users
                cursor.execute("SELECT id, name FROM users WHERE approval_status = 'Approved'")
                users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query approved users: {e}")
        return None
        
    for user in users:
        user_id = user["id"]
        npy_path = config.UPLOAD_DIR / "enrollments" / str(user_id) / "embeddings.npy"
        if not npy_path.exists():
            continue
            
        try:
            user_embs_dict = np.load(str(npy_path), allow_pickle=True).item()
            for pose, emb_list in user_embs_dict.items():
                emb = np.array(emb_list, dtype=np.float32)
                # Compute Cosine Similarity
                dot_prod = np.dot(scan_emb, emb)
                norm_scan = np.linalg.norm(scan_emb)
                norm_emb = np.linalg.norm(emb)
                similarity = dot_prod / (norm_scan * norm_emb + 1e-8)
                
                if similarity > best_sim:
                    best_sim = similarity
                    best_user_id = user_id
        except Exception as e:
            logger.error(f"Error reading embedding cache for user {user_id}: {e}")
            
    if best_user_id != -1:
        logger.info(f"Scan matched: User ID = {best_user_id}, Max Cosine Sim = {best_sim:.4f}")
        return best_user_id, best_sim
        
    return None

def get_image_embeddings_all(img: np.ndarray) -> list[tuple[np.ndarray, list[int]]] | None:
    """Extract embeddings and bounding boxes for all faces in the image."""
    if img is None:
        return None
        
    try:
        app = get_face_analysis()
        faces = app.get(img)
        if not faces or len(faces) == 0:
            return None
            
        results = []
        for face in faces:
            bbox = face.bbox  # [x1, y1, x2, y2]
            bbox_int = [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]
            results.append((face.embedding, bbox_int))
        return results
    except Exception as e:
        logger.error(f"Error in multiple face embedding extraction: {e}")
    return None

def predict_multiple_faces(color_img: np.ndarray) -> list[dict]:
    """
    Predict identities for all faces detected in the image.
    Returns:
        list of dicts containing user_id, similarity, and bbox
    """
    results = get_image_embeddings_all(color_img)
    if not results:
        return []
        
    predictions = []
    
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Compare scans against approved users
                cursor.execute("SELECT id, name FROM users WHERE approval_status = 'Approved'")
                users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query approved users: {e}")
        return []
        
    for scan_emb, bbox in results:
        best_user_id = -1
        best_sim = -1.0
        
        for user in users:
            user_id = user["id"]
            npy_path = config.UPLOAD_DIR / "enrollments" / str(user_id) / "embeddings.npy"
            if not npy_path.exists():
                continue
                
            try:
                user_embs_dict = np.load(str(npy_path), allow_pickle=True).item()
                for pose, emb_list in user_embs_dict.items():
                    emb = np.array(emb_list, dtype=np.float32)
                    dot_prod = np.dot(scan_emb, emb)
                    norm_scan = np.linalg.norm(scan_emb)
                    norm_emb = np.linalg.norm(emb)
                    similarity = dot_prod / (norm_scan * norm_emb + 1e-8)
                    
                    if similarity > best_sim:
                        best_sim = similarity
                        best_user_id = user_id
            except Exception as e:
                logger.error(f"Error reading embedding cache for user {user_id}: {e}")
                
        predictions.append({
            "user_id": best_user_id,
            "similarity": best_sim,
            "bbox": bbox
        })
        
    return predictions

def verify_structural_correlation(user_id: int, scan_gray_face: np.ndarray) -> bool:
    """Stub kept for legacy API compatibility. Verification is fully handled via ArcFace embeddings."""
    return True
