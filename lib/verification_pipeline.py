import uuid
import logging
import base64
from datetime import datetime
from typing import Dict, Any
from io import BytesIO

from database.pinecone import pinecone_manager
from services.embedding import embedding_service
from . import image_processor
from . import manipulation_detector
from . import vlm_verifier
from services.scoring import scoring_engine
from utils.logger import get_logger

logger = get_logger(__name__)

class VerificationPipeline:
    def __init__(self):
        self.pinecone = pinecone_manager
    
    async def ingest_complaint(self, 
                              complaint_id: str,
                              image_bytes: bytes,
                              lat: float,
                              lon: float,
                              ts_iso: str,
                              metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Ingest complaint with before-state image"""
        try:
            media_id = str(uuid.uuid4())
            
            # Compute embedding and pHash
            embedding = embedding_service.get_clip_embedding(image_bytes)
            phash = image_processor.compute_phash(image_bytes)
            
            # Create thumbnail
            thumbnail = embedding_service.create_thumbnail(image_bytes)
            
            # Chunk the full image
            chunks = image_processor.chunk_image(image_bytes)
            chunk_ids = []
            
            # Store chunks
            for chunk in chunks:
                chunk_id = f"complaint::{complaint_id}::media::{media_id}#chunk::{chunk['index']}"
                # Use minimal non-zero vector for metadata storage
                metadata_vector = [0.001] + [0.0] * 511
                self.pinecone.upsert_vector(
                    'chunks',
                    chunk_id,
                    metadata_vector,
                    {
                        'chunk_index': chunk['index'],
                        'bytes_len': chunk['size'],
                        'b64': chunk['b64']
                    }
                )
                chunk_ids.append(chunk_id)
            
            # Store thumbnail chunk
            thumb_chunk_id = f"complaint::{complaint_id}::media::{media_id}#thumb"
            thumb_b64 = base64.b64encode(thumbnail).decode('utf-8')
            metadata_vector = [0.001] + [0.0] * 511
            self.pinecone.upsert_vector(
                'chunks',
                thumb_chunk_id,
                metadata_vector,
                {
                    'chunk_index': -1,
                    'bytes_len': len(thumbnail),
                    'b64': thumb_b64
                }
            )
            
            # Store complaint before record
            complaint_metadata = {
                'complaint_id': complaint_id,
                'media_id': media_id,
                'ts_iso': ts_iso,
                'lat': lat,
                'lon': lon,
                'pHash': phash,
                'chunks': chunk_ids,
                'thumb_chunk': thumb_chunk_id,
                **(metadata or {})
            }
            
            vector_id = f"complaint::{complaint_id}::media::{media_id}"
            self.pinecone.upsert_vector('complaints_before', vector_id, embedding, complaint_metadata)
            
            logger.info(f"Ingested complaint {complaint_id} with media {media_id}")
            
            return {
                'complaint_id': complaint_id,
                'media_id': media_id,
                'status': 'ingested'
            }
            
        except Exception as e:
            logger.error(f"Error ingesting complaint: {e}")
            raise
    
    async def ingest_proof(self,
                          proof_id: str,
                          complaint_id: str,
                          worker_id: str,
                          image_bytes: bytes,
                          lat: float,
                          lon: float,
                          ts_iso: str,
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Ingest proof/after-state image"""
        try:
            # Compute embedding and pHash
            embedding = embedding_service.get_clip_embedding(image_bytes)
            phash = image_processor.compute_phash(image_bytes)
            
            # Create thumbnail
            thumbnail = embedding_service.create_thumbnail(image_bytes)
            
            # Chunk the full image
            chunks = image_processor.chunk_image(image_bytes)
            chunk_ids = []
            
            # Store chunks
            for chunk in chunks:
                chunk_id = f"proof::{proof_id}#chunk::{chunk['index']}"
                metadata_vector = [0.001] + [0.0] * 511
                self.pinecone.upsert_vector(
                    'chunks',
                    chunk_id,
                    metadata_vector,
                    {
                        'chunk_index': chunk['index'],
                        'bytes_len': chunk['size'],
                        'b64': chunk['b64']
                    }
                )
                chunk_ids.append(chunk_id)
            
            # Store thumbnail chunk
            thumb_chunk_id = f"proof::{proof_id}#thumb"
            thumb_b64 = base64.b64encode(thumbnail).decode('utf-8')
            metadata_vector = [0.001] + [0.0] * 511
            self.pinecone.upsert_vector(
                'chunks',
                thumb_chunk_id,
                metadata_vector,
                {
                    'chunk_index': -1,
                    'bytes_len': len(thumbnail),
                    'b64': thumb_b64
                }
            )
            
            # Check for duplicates in phash_index
            metadata_vector = [0.001] + [0.0] * 511
            phash_results = self.pinecone.query_vectors('phash_index', metadata_vector, top_k=100)
            recycled_flag = False
            
            for match in phash_results.matches:
                existing_phash = match.metadata.get('phash', '')
                if image_processor.is_duplicate(phash, existing_phash):
                    recycled_flag = True
                    logger.warning(f"Duplicate image detected for proof {proof_id}")
                    break
            
            # Store proof record
            proof_metadata = {
                'proof_id': proof_id,
                'complaint_id': complaint_id,
                'worker_id': worker_id,
                'ts_iso': ts_iso,
                'lat': lat,
                'lon': lon,
                'pHash': phash,
                'chunks': chunk_ids,
                'thumb_chunk': thumb_chunk_id,
                'recycled_flag': recycled_flag,
                'size_bytes': len(image_bytes),
                **(metadata or {})
            }
            
            vector_id = f"proof::{proof_id}"
            self.pinecone.upsert_vector('proofs', vector_id, embedding, proof_metadata)
            
            # Update phash index
            phash_vector_id = f"phash::{phash}"
            metadata_vector = [0.001] + [0.0] * 511
            existing_phash_record = None
            try:
                existing_phash_record = self.pinecone.fetch_vector('phash_index', phash_vector_id)
            except:
                pass
            
            if existing_phash_record:
                proof_ids = existing_phash_record.metadata.get('proof_ids', [])
                proof_ids.append(proof_id)
                self.pinecone.upsert_vector(
                    'phash_index',
                    phash_vector_id,
                    metadata_vector,
                    {
                        'phash': phash,
                        'proof_ids': proof_ids,
                        'last_seen': ts_iso
                    }
                )
            else:
                self.pinecone.upsert_vector(
                    'phash_index',
                    phash_vector_id,
                    metadata_vector,
                    {
                        'phash': phash,
                        'proof_ids': [proof_id],
                        'last_seen': ts_iso
                    }
                )
            
            logger.info(f"Ingested proof {proof_id}")
            
            return {
                'proof_id': proof_id,
                'status': 'ingested',
                'recycled_flag': recycled_flag
            }
            
        except Exception as e:
            logger.error(f"Error ingesting proof: {e}")
            raise
    
    async def verify_proof(self, proof_id: str) -> Dict[str, Any]:
        """Run full verification pipeline on a proof"""
        try:
            start_time = datetime.now()
            
            # Fetch proof record
            proof_vector = self.pinecone.fetch_vector('proofs', f"proof::{proof_id}")
            if not proof_vector:
                raise ValueError(f"Proof {proof_id} not found")
            
            proof_meta = proof_vector.metadata
            complaint_id = proof_meta.get('complaint_id')
            
            # Fetch complaint record
            metadata_vector = [0.001] + [0.0] * 511
            complaint_results = self.pinecone.query_vectors(
                'complaints_before',
                metadata_vector,
                top_k=1,
                filter_dict={'complaint_id': complaint_id}
            )
            
            if not complaint_results.matches:
                raise ValueError(f"Complaint {complaint_id} not found")
            
            complaint_match = complaint_results.matches[0]
            complaint_meta = complaint_match.metadata
            
            # Fetch thumbnails
            proof_thumb_chunk = self.pinecone.fetch_vector('chunks', proof_meta['thumb_chunk'])
            complaint_thumb_chunk = self.pinecone.fetch_vector('chunks', complaint_meta['thumb_chunk'])
            
            proof_thumb_b64 = proof_thumb_chunk.metadata['b64']
            complaint_thumb_b64 = complaint_thumb_chunk.metadata['b64']
            
            # Reconstruct thumbnail bytes for similarity computation
            proof_thumb_bytes = base64.b64decode(proof_thumb_b64)
            complaint_thumb_bytes = base64.b64decode(complaint_thumb_b64)
            
            # Compute embedding similarity
            embedding_sim = 1.0 - (proof_vector.score if hasattr(proof_vector, 'score') else 0.5)
            
            # Compute image similarity metrics
            similarity_metrics = image_processor.compute_image_similarity(
                complaint_thumb_bytes,
                proof_thumb_bytes
            )
            
            # Calculate distance
            distance_m = scoring_engine.haversine_distance(
                complaint_meta['lat'],
                complaint_meta['lon'],
                proof_meta['lat'],
                proof_meta['lon']
            )
            
            # Check for manipulation (only if needed for efficiency)
            recycled_flag = proof_meta.get('recycled_flag', False)
            manipulation_result = {'manipulation_probability': 0.0}
            
            if recycled_flag or distance_m > 50:
                # Run manipulation detection on full image
                full_image_bytes = await self._reconstruct_full_image(proof_meta['chunks'])
                manipulation_result = manipulation_detector.detect_manipulation(full_image_bytes)
            
            # Query for few-shot examples
            few_shot_examples = []
            try:
                ref_results = self.pinecone.query_vectors(
                    'verified_reference_pairs',
                    proof_vector.values,
                    top_k=3
                )
                few_shot_examples = [
                    {'description': m.metadata.get('notes', '')}
                    for m in ref_results.matches
                ]
            except:
                pass
            
            # VLM verification
            vlm_metadata = {
                'complaint_ts': complaint_meta.get('ts_iso'),
                'proof_ts': proof_meta.get('ts_iso'),
                'distance_m': distance_m,
                'embedding_sim': embedding_sim,
                'ssim': similarity_metrics['ssim'],
                'pixel_diff_norm': similarity_metrics['pixel_diff_norm'],
                'manip_prob': manipulation_result['manipulation_probability'],
                'recycled_flag': recycled_flag,
                'worker_present': True,  # TODO: Check worker traces
                'issue_type': complaint_meta.get('issue_type', 'general')
            }
            
            vlm_result = vlm_verifier.verify_with_vlm(
                complaint_thumb_b64,
                proof_thumb_b64,
                vlm_metadata,
                few_shot_examples
            )
            
            # Scoring
            scoring_signals = {
                'embedding_sim': embedding_sim,
                'ssim': similarity_metrics['ssim'],
                'pixel_diff_norm': similarity_metrics['pixel_diff_norm'],
                'vlm_work_completion_score': vlm_result['work_completion_score'],
                'distance_m': distance_m,
                'manipulation_probability': manipulation_result['manipulation_probability'],
                'recycled_flag': recycled_flag,
                'worker_present': True
            }
            
            score_data = scoring_engine.compute_composite_score(scoring_signals)
            decision = scoring_engine.make_decision(score_data['composite_score'], scoring_signals)
            explanation = scoring_engine.generate_explanation(decision, score_data, scoring_signals)
            
            # Build final report
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            report = {
                'proof_id': proof_id,
                'complaint_id': complaint_id,
                'verification_status': decision,
                'verification_timestamp': datetime.now().isoformat(),
                'location_validation': {
                    'distance_from_complaint_meters': distance_m,
                    'within_acceptable_radius': distance_m <= 50,
                    'validation_passed': distance_m <= 50
                },
                'image_analysis': {
                    'before_after_comparison': {
                        'visual_change_detected': vlm_result['visual_change_detected'],
                        'change_description': vlm_result['change_description'],
                        'improvement_visible': vlm_result['improvement_visible']
                    },
                    'quality_assessment': {
                        'work_completion_score': vlm_result['work_completion_score'],
                        'issues_detected': vlm_result['issues_detected'],
                        'meets_standards': vlm_result['meets_standards']
                    },
                    'authenticity_check': {
                        'is_original_photo': not recycled_flag,
                        'recycled_photo_detected': recycled_flag,
                        'manipulation_detected': manipulation_result['manipulation_probability'] >= 0.85,
                        'fraud_risk_score': vlm_result['fraud_risk_score']
                    }
                },
                'timeline_validation': {
                    'worker_at_location': True,
                    'time_spent_minutes': 0,
                    'reasonable_duration': True
                },
                'scoring': {
                    'composite_score': score_data['composite_score'],
                    'components': score_data['components']
                },
                'explanation': explanation,
                'vlm_explanation': vlm_result['explanation'],
                'recommendation': vlm_result['recommendation'],
                'flagged_for_review': decision == 'QUESTIONABLE',
                'processing_time_ms': processing_time_ms
            }
            
            # Store audit record
            audit_id = str(uuid.uuid4())
            audit_b64 = base64.b64encode(str(report).encode('utf-8')).decode('utf-8')
            metadata_vector = [0.001] + [0.0] * 511
            self.pinecone.upsert_vector(
                'audits',
                f"audit::{audit_id}",
                metadata_vector,
                {
                    'full_json_report_b64': audit_b64,
                    'proof_id': proof_id,
                    'complaint_id': complaint_id,
                    'decision': decision
                }
            )
            
            logger.info(f"Verification completed for proof {proof_id}: {decision}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error verifying proof {proof_id}: {e}")
            raise
    
    async def _reconstruct_full_image(self, chunk_ids: list) -> bytes:
        """Reconstruct full image from chunk IDs"""
        chunks = []
        for chunk_id in chunk_ids:
            chunk_vector = self.pinecone.fetch_vector('chunks', chunk_id)
            if chunk_vector:
                chunks.append({
                    'index': chunk_vector.metadata['chunk_index'],
                    'b64': chunk_vector.metadata['b64']
                })
        
        return image_processor.reconstruct_image(chunks)

verification_pipeline = VerificationPipeline()
