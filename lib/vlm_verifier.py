import os
import json
import openai
from typing import Dict, Any
from settings import OPENAI_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

class VLMVerifier:
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def build_vlm_prompt(self, 
                        before_image_b64: str,
                        after_image_b64: str,
                        metadata: Dict[str, Any],
                        few_shot_examples: list = None) -> list:
        """Build GPT-4V prompt with images and metadata"""
        
        # Few-shot examples context
        examples_text = ""
        if few_shot_examples:
            examples_text = "\n\nCONTEXT: Here are verified examples for reference:\n"
            for i, example in enumerate(few_shot_examples[:3], 1):
                examples_text += f"\nEXAMPLE {i}: {example.get('description', 'Verified work completion')}\n"
        
        prompt_text = f"""{examples_text}

TASK:
Compare BEFORE image with PROOF (AFTER) image to verify work completion.

Metadata:
- Complaint Timestamp: {metadata.get('complaint_ts', 'N/A')}
- Proof Timestamp: {metadata.get('proof_ts', 'N/A')}
- Distance from complaint location: {metadata.get('distance_m', 'N/A')} meters
- Embedding Similarity: {metadata.get('embedding_sim', 0):.3f}
- SSIM: {metadata.get('ssim', 0):.3f}
- Pixel Difference: {metadata.get('pixel_diff_norm', 0):.3f}
- Manipulation Probability: {metadata.get('manip_prob', 0):.3f}
- Recycled Photo Flag: {metadata.get('recycled_flag', False)}
- Worker Present: {metadata.get('worker_present', False)}
- Issue Type: {metadata.get('issue_type', 'general')}

Return STRICT JSON (no markdown, no code blocks, just raw JSON):
{{
  "visual_change_detected": boolean,
  "change_description": "short text (max 40 words)",
  "improvement_visible": boolean,
  "work_completion_score": int (1-10),
  "issues_detected": ["list of issues"],
  "meets_standards": boolean,
  "manipulation_detected": boolean,
  "fraud_risk_score": float (0-1),
  "recommendation": "approve"|"reject"|"human_review",
  "explanation": "detailed reasoning referencing visible cues and metadata"
}}
"""
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert work verification agent. Analyze before and after images to verify work completion. Return ONLY valid JSON without any markdown formatting or code blocks."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{before_image_b64}"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{after_image_b64}"
                        }
                    }
                ]
            }
        ]
        
        return messages
    
    def verify_with_vlm(self,
                       before_image_b64: str,
                       after_image_b64: str,
                       metadata: Dict[str, Any],
                       few_shot_examples: list = None) -> Dict[str, Any]:
        """Call GPT-4V to verify work completion"""
        try:
            messages = self.build_vlm_prompt(before_image_b64, after_image_b64, metadata, few_shot_examples)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4O which has vision capabilities
                messages=messages,
                max_tokens=1000,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                # Remove ```json or ``` from start and ``` from end
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines[-1].startswith('```'):
                    lines = lines[:-1]
                content = '\n'.join(lines)
            
            # Parse JSON response
            vlm_result = json.loads(content)
            
            logger.info("VLM verification completed successfully")
            return vlm_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing VLM JSON response: {e}")
            logger.error(f"Raw response: {content if 'content' in locals() else 'No response'}")
            # Return default response
            return {
                "visual_change_detected": False,
                "change_description": "Error parsing VLM response",
                "improvement_visible": False,
                "work_completion_score": 1,
                "issues_detected": ["VLM processing error"],
                "meets_standards": False,
                "manipulation_detected": False,
                "fraud_risk_score": 0.5,
                "recommendation": "human_review",
                "explanation": "Failed to parse VLM output, requires manual review"
            }
        except Exception as e:
            logger.error(f"Error in VLM verification: {e}")
            return {
                "visual_change_detected": False,
                "change_description": "VLM error",
                "improvement_visible": False,
                "work_completion_score": 1,
                "issues_detected": ["VLM service error"],
                "meets_standards": False,
                "manipulation_detected": False,
                "fraud_risk_score": 0.5,
                "recommendation": "human_review",
                "explanation": f"VLM service error: {str(e)}"
            }

vlm_verifier = VLMVerifier()
