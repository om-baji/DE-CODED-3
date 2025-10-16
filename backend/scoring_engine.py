import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ScoringEngine:
    def __init__(self):
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'visual_similarity': 0.35,
            'visual_diff': 0.20,
            'vlm_quality': 0.20,
            'spatial_proximity': 0.10,
            'authenticity': 0.10,
            'recycled_penalty': -0.5,
            'manipulation_penalty': -0.3
        }
        
        # Thresholds for decisions
        self.thresholds = {
            'verified': 0.70,
            'questionable': 0.45
        }
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in meters"""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def normalize(self, value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Normalize value to [0, 1] range"""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
    
    def compute_composite_score(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Compute composite verification score from multiple signals"""
        
        # Extract signals with defaults
        embedding_sim = signals.get('embedding_sim', 0.0)
        ssim = signals.get('ssim', 0.0)
        pixel_diff_norm = signals.get('pixel_diff_norm', 1.0)
        vlm_score = signals.get('vlm_work_completion_score', 1) / 10.0  # Normalize to [0,1]
        distance_m = signals.get('distance_m', 1000)
        manip_prob = signals.get('manipulation_probability', 0.0)
        recycled_flag = signals.get('recycled_flag', False)
        worker_present = signals.get('worker_present', False)
        
        # Compute component scores
        visual_score = self.normalize(embedding_sim, 0.0, 1.0) * self.weights['visual_similarity']
        diff_score = self.normalize(1.0 - ssim, 0.0, 1.0) * self.weights['visual_diff']
        quality_score = vlm_score * self.weights['vlm_quality']
        
        # Spatial score (within 50m = 0.10, beyond = 0.0)
        spatial_score = self.weights['spatial_proximity'] if distance_m <= 50 else 0.0
        
        # Authenticity score
        authenticity_score = (1.0 - manip_prob) * self.weights['authenticity']
        
        # Penalties
        recycled_penalty = self.weights['recycled_penalty'] if recycled_flag else 0.0
        manipulation_penalty = self.weights['manipulation_penalty'] if manip_prob >= 0.85 else 0.0
        
        # Composite score
        composite_score = (
            visual_score + diff_score + quality_score + 
            spatial_score + authenticity_score + 
            recycled_penalty + manipulation_penalty
        )
        
        # Clamp to [0, 1]
        composite_score = max(0.0, min(1.0, composite_score))
        
        return {
            'composite_score': composite_score,
            'components': {
                'visual_similarity_score': visual_score,
                'visual_diff_score': diff_score,
                'vlm_quality_score': quality_score,
                'spatial_proximity_score': spatial_score,
                'authenticity_score': authenticity_score,
                'recycled_penalty': recycled_penalty,
                'manipulation_penalty': manipulation_penalty
            }
        }
    
    def make_decision(self, composite_score: float, signals: Dict[str, Any]) -> str:
        """Make verification decision based on score and critical checks"""
        
        # Critical failure checks
        recycled_flag = signals.get('recycled_flag', False)
        manip_prob = signals.get('manipulation_probability', 0.0)
        distance_m = signals.get('distance_m', 0)
        
        # Check critical failures
        if recycled_flag:
            return 'REJECTED'  # Recycled photo
        
        if manip_prob >= 0.85:
            return 'REJECTED'  # High manipulation probability
        
        if distance_m > 50:
            return 'REJECTED'  # Location mismatch
        
        # Score-based decision
        if composite_score >= self.thresholds['verified']:
            return 'VERIFIED'
        elif composite_score >= self.thresholds['questionable']:
            return 'QUESTIONABLE'
        else:
            return 'REJECTED'
    
    def generate_explanation(self, decision: str, score_data: Dict[str, Any], signals: Dict[str, Any]) -> str:
        """Generate human-readable explanation for the decision"""
        composite_score = score_data['composite_score']
        components = score_data['components']
        
        explanation = f"Verification Decision: {decision} (Score: {composite_score:.2f})\n\n"
        
        if decision == 'REJECTED':
            if signals.get('recycled_flag'):
                explanation += "❌ Critical Failure: Recycled photo detected\n"
            if signals.get('manipulation_probability', 0) >= 0.85:
                explanation += "❌ Critical Failure: High manipulation probability detected\n"
            if signals.get('distance_m', 0) > 50:
                explanation += "❌ Critical Failure: Location mismatch (beyond 50m radius)\n"
        
        explanation += f"\nScore Breakdown:\n"
        explanation += f"- Visual Similarity: {components['visual_similarity_score']:.3f}\n"
        explanation += f"- Visual Change: {components['visual_diff_score']:.3f}\n"
        explanation += f"- VLM Quality Assessment: {components['vlm_quality_score']:.3f}\n"
        explanation += f"- Spatial Proximity: {components['spatial_proximity_score']:.3f}\n"
        explanation += f"- Authenticity: {components['authenticity_score']:.3f}\n"
        
        if components['recycled_penalty'] < 0:
            explanation += f"- Recycled Penalty: {components['recycled_penalty']:.3f}\n"
        if components['manipulation_penalty'] < 0:
            explanation += f"- Manipulation Penalty: {components['manipulation_penalty']:.3f}\n"
        
        return explanation

scoring_engine = ScoringEngine()
