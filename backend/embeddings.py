import os
import base64
from io import BytesIO
from PIL import Image
import openai
import logging
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def encode_image_to_base64(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def decode_base64_to_image(self, base64_str: str) -> Image.Image:
        """Decode base64 string to PIL Image"""
        image_bytes = base64.b64decode(base64_str)
        return Image.open(BytesIO(image_bytes))
    
    def get_clip_embedding(self, image_bytes: bytes) -> list:
        """Get CLIP embedding for an image using OpenAI
        Note: OpenAI doesn't provide direct CLIP embeddings via API,
        so we'll use a workaround with vision model or local CLIP.
        For now, returning a mock embedding for demo purposes.
        """
        try:
            # For production, you would use:
            # 1. sentence-transformers/clip-vit-large-patch14 locally
            # 2. Or a dedicated embedding service
            
            # Mock embedding for now (512 dimensions)
            # In production, replace this with actual CLIP model
            from PIL import Image
            import io
            
            # Create a simple hash-based embedding for demo
            img = Image.open(io.BytesIO(image_bytes))
            img_array = np.array(img.resize((224, 224)))
            
            # Simple feature extraction (replace with actual CLIP)
            features = img_array.flatten()[:512]
            # Normalize
            embedding = features / (np.linalg.norm(features) + 1e-8)
            
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating CLIP embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 512
    
    def create_thumbnail(self, image_bytes: bytes, size=(320, 320), quality=60) -> bytes:
        """Create a compressed thumbnail from image bytes"""
        img = Image.open(BytesIO(image_bytes))
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()

embedding_service = EmbeddingService()
