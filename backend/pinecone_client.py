import os
from pinecone import Pinecone, ServerlessSpec
import logging

logger = logging.getLogger(__name__)

class PineconeManager:
    def __init__(self):
        from dotenv import load_dotenv
        from pathlib import Path
        ROOT_DIR = Path(__file__).parent
        load_dotenv(ROOT_DIR / '.env')
        
        self.api_key = os.environ.get('PINECONE_API_KEY')
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not found in environment")
        
        self.pc = Pinecone(api_key=self.api_key)
        self.dimension = 512  # CLIP ViT-L/14 embedding dimension
        
        # Using existing indexes with namespaces to work within free tier limit (5 indexes)
        # We'll use: complaints-before, proofs, and metadata-store
        self.index_map = {
            'complaints_before': ('complaints-before', ''),  # No namespace, use root
            'proofs': ('proofs', ''),  # No namespace, use root
            'verified_reference_pairs': ('proofs', 'reference_pairs'),  # Namespace in proofs
            'chunks': ('metadata-store', 'chunks'),  # metadata-store for metadata
            'phash_index': ('metadata-store', 'phash'),
            'worker_traces': ('metadata-store', 'worker_traces'),
            'audits': ('metadata-store', 'audits')
        }
        
    def initialize_indexes(self):
        """Verify required Pinecone indexes exist"""
        required_indexes = ['complaints-before', 'proofs', 'metadata-store']
        
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        for index_name in required_indexes:
            if index_name in existing_indexes:
                logger.info(f"Index {index_name} exists and is ready")
            else:
                logger.warning(f"Index {index_name} not found! Please create it manually.")
        
        logger.info("All required indexes verified")
    
    def get_index(self, index_type: str):
        """Get a specific Pinecone index with namespace"""
        if index_type not in self.index_map:
            raise ValueError(f"Unknown index type: {index_type}")
        index_name, namespace = self.index_map[index_type]
        # Return tuple of (index, namespace) for use in upsert/query
        return (self.pc.Index(index_name), namespace)
    
    def upsert_vector(self, index_type: str, vector_id: str, vector: list, metadata: dict):
        """Upsert a single vector to specified index/namespace"""
        index, namespace = self.get_index(index_type)
        if namespace:
            index.upsert(vectors=[(vector_id, vector, metadata)], namespace=namespace)
        else:
            index.upsert(vectors=[(vector_id, vector, metadata)])
        logger.info(f"Upserted vector {vector_id} to {index_type}")
    
    def query_vectors(self, index_type: str, vector: list, top_k: int = 5, filter_dict: dict = None):
        """Query vectors from specified index/namespace"""
        index, namespace = self.get_index(index_type)
        if namespace:
            results = index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict,
                namespace=namespace
            )
        else:
            results = index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
        return results
    
    def fetch_vector(self, index_type: str, vector_id: str):
        """Fetch a specific vector by ID from index/namespace"""
        index, namespace = self.get_index(index_type)
        if namespace:
            result = index.fetch(ids=[vector_id], namespace=namespace)
        else:
            result = index.fetch(ids=[vector_id])
        return result.vectors.get(vector_id)

# Global instance
pinecone_manager = PineconeManager()
