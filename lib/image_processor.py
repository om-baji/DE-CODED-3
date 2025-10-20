import imagehash
from PIL import Image
from io import BytesIO
import base64
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

class ImageProcessor:
    def __init__(self):
        self.chunk_size = 20 * 1024  # 20KB raw -> ~27KB base64
    
    def compute_phash(self, image_bytes: bytes) -> str:
        """Compute perceptual hash of an image"""
        try:
            img = Image.open(BytesIO(image_bytes))
            phash = imagehash.phash(img)
            return str(phash)
        except Exception as e:
            logger.error(f"Error computing pHash: {e}")
            return ""
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes"""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except:
            return 100  # Return high distance on error
    
    def is_duplicate(self, hash1: str, hash2: str, threshold: float = 0.90) -> bool:
        """Check if two images are duplicates based on pHash similarity"""
        distance = self.hamming_distance(hash1, hash2)
        max_distance = 64  # For 64-bit hash
        similarity = 1 - (distance / max_distance)
        return similarity >= threshold
    
    def chunk_image(self, image_bytes: bytes) -> list:
        """Split image bytes into chunks for Pinecone storage"""
        chunks = []
        total_size = len(image_bytes)
        num_chunks = (total_size + self.chunk_size - 1) // self.chunk_size
        
        for i in range(num_chunks):
            start = i * self.chunk_size
            end = min(start + self.chunk_size, total_size)
            chunk = image_bytes[start:end]
            chunk_b64 = base64.b64encode(chunk).decode('utf-8')
            chunks.append({
                'index': i,
                'b64': chunk_b64,
                'size': len(chunk)
            })
        
        return chunks
    
    def reconstruct_image(self, chunks: list) -> bytes:
        """Reconstruct image from chunks"""
        # Sort by index
        sorted_chunks = sorted(chunks, key=lambda x: x['index'])
        image_bytes = b''
        
        for chunk in sorted_chunks:
            chunk_bytes = base64.b64decode(chunk['b64'])
            image_bytes += chunk_bytes
        
        return image_bytes
    
    def compute_image_similarity(self, img1_bytes: bytes, img2_bytes: bytes) -> dict:
        """Compute various similarity metrics between two images"""
        from skimage.metrics import structural_similarity as ssim
        import cv2
        
        try:
            # Load images
            img1 = Image.open(BytesIO(img1_bytes)).convert('RGB')
            img2 = Image.open(BytesIO(img2_bytes)).convert('RGB')
            
            # Resize to same dimensions
            size = (256, 256)
            img1 = img1.resize(size)
            img2 = img2.resize(size)
            
            # Convert to numpy arrays
            img1_array = np.array(img1)
            img2_array = np.array(img2)
            
            # Convert to grayscale for SSIM
            img1_gray = cv2.cvtColor(img1_array, cv2.COLOR_RGB2GRAY)
            img2_gray = cv2.cvtColor(img2_array, cv2.COLOR_RGB2GRAY)
            
            # Compute SSIM
            ssim_score = ssim(img1_gray, img2_gray)
            
            # Compute pixel difference
            pixel_diff = np.abs(img1_array.astype(float) - img2_array.astype(float))
            pixel_diff_norm = np.mean(pixel_diff) / 255.0
            
            return {
                'ssim': float(ssim_score),
                'pixel_diff_norm': float(pixel_diff_norm),
                'visual_change': pixel_diff_norm > 0.1  # Threshold for change detection
            }
        except Exception as e:
            logger.error(f"Error computing image similarity: {e}")
            return {
                'ssim': 0.0,
                'pixel_diff_norm': 1.0,
                'visual_change': True
            }

image_processor = ImageProcessor()
