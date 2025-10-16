import numpy as np
from PIL import Image
from io import BytesIO
import cv2
import logging
from tensorflow import keras
from keras.applications import Xception
from keras.applications.xception import preprocess_input

logger = logging.getLogger(__name__)

class ManipulationDetector:
    def __init__(self):
        # Load pre-trained Xception model for deepfake/manipulation detection
        # In production, you'd fine-tune this on manipulation datasets
        try:
            self.model = Xception(weights='imagenet', include_top=False, pooling='avg')
            logger.info("Xception model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Xception model: {e}")
            self.model = None
    
    def compute_ela(self, image_bytes: bytes, quality: int = 95) -> np.ndarray:
        """Compute Error Level Analysis (ELA) for image manipulation detection"""
        try:
            # Load original image
            img = Image.open(BytesIO(image_bytes))
            
            # Save at specified quality
            temp_buffer = BytesIO()
            img.save(temp_buffer, 'JPEG', quality=quality)
            temp_buffer.seek(0)
            
            # Load recompressed image
            compressed_img = Image.open(temp_buffer)
            
            # Compute difference
            img_array = np.array(img).astype(float)
            compressed_array = np.array(compressed_img).astype(float)
            
            ela = np.abs(img_array - compressed_array)
            ela_normalized = (ela / ela.max() * 255).astype(np.uint8)
            
            return ela_normalized
        except Exception as e:
            logger.error(f"Error computing ELA: {e}")
            return np.zeros((100, 100, 3), dtype=np.uint8)
    
    def detect_manipulation_cnn(self, image_bytes: bytes) -> float:
        """Use CNN to detect image manipulation"""
        if self.model is None:
            logger.warning("CNN model not loaded, returning default score")
            return 0.1  # Low manipulation probability as default
        
        try:
            # Preprocess image
            img = Image.open(BytesIO(image_bytes)).convert('RGB')
            img = img.resize((299, 299))  # Xception input size
            img_array = np.array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            # Get features
            features = self.model.predict(img_array, verbose=0)
            
            # Simple heuristic: check feature variance
            # High variance in features might indicate manipulation
            # This is a placeholder - in production, use a fine-tuned classifier
            feature_variance = np.var(features)
            manipulation_score = min(1.0, feature_variance / 100.0)  # Normalize
            
            return float(manipulation_score)
        except Exception as e:
            logger.error(f"Error in CNN manipulation detection: {e}")
            return 0.1
    
    def detect_manipulation(self, image_bytes: bytes) -> dict:
        """Comprehensive manipulation detection combining ELA and CNN"""
        # Compute ELA
        ela_result = self.compute_ela(image_bytes)
        ela_score = np.mean(ela_result) / 255.0  # Normalize to [0, 1]
        
        # Run CNN detection
        cnn_score = self.detect_manipulation_cnn(image_bytes)
        
        # Combine scores (weighted average)
        composite_score = (ela_score * 0.4 + cnn_score * 0.6)
        
        # Determine if manipulated (threshold at 0.85 as per requirements)
        is_manipulated = composite_score >= 0.85
        
        return {
            'manipulation_probability': float(composite_score),
            'ela_score': float(ela_score),
            'cnn_score': float(cnn_score),
            'is_manipulated': is_manipulated,
            'ela_heatmap_available': True
        }

manipulation_detector = ManipulationDetector()
