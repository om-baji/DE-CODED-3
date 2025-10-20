import os
from pinecone import Pinecone
from settings import PINECONE_API_KEY
from utils.logger import get_logger
logger = get_logger(__name__)


class PineconeManager:
    def __init__(self):
        self.api_key = PINECONE_API_KEY
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY not found in environment or settings")

        self.pc = Pinecone(api_key=self.api_key)
        self.dimension = 512  # CLIP ViT-L/14 embedding dimension
        self.index_map = self._build_index_map()

    def _build_index_map(self):
        return {
            "complaints_before": ("complaints-before", ""),
            "proofs": ("proofs", ""),
            "verified_reference_pairs": ("proofs", "reference_pairs"),
            "chunks": ("metadata-store", "chunks"),
            "phash_index": ("metadata-store", "phash"),
            "worker_traces": ("metadata-store", "worker_traces"),
            "audits": ("metadata-store", "audits"),
        }

    def _get_index_and_namespace(self, index_type: str):
        if index_type not in self.index_map:
            raise ValueError(f"Unknown index type: {index_type}")
        index_name, namespace = self.index_map[index_type]
        return self.pc.Index(index_name), namespace

    def _apply_namespace(self, namespace: str, kwargs: dict):
        if namespace:
            kwargs["namespace"] = namespace
        return kwargs

    def initialize_indexes(self):
        required_indexes = {"complaints-before", "proofs", "metadata-store"}
        existing_indexes = {idx.name for idx in self.pc.list_indexes()}

        for index_name in required_indexes:
            if index_name in existing_indexes:
                logger.info(f"Index {index_name} exists and is ready")
            else:
                logger.warning(
                    f"Index {index_name} not found! Please create it manually."
                )

        logger.info("All required indexes verified")

    def get_index(self, index_type: str):
        return self._get_index_and_namespace(index_type)

    def upsert_vector(
        self, index_type: str, vector_id: str, vector: list, metadata: dict
    ):
        index, namespace = self._get_index_and_namespace(index_type)
        kwargs = self._apply_namespace(
            namespace, {"vectors": [(vector_id, vector, metadata)]}
        )
        index.upsert(**kwargs)
        logger.info(f"Upserted vector {vector_id} to index '{index_type}'")

    def query_vectors(
        self, index_type: str, vector: list, top_k: int = 5, filter_dict: dict = None
    ):
        index, namespace = self._get_index_and_namespace(index_type)
        kwargs = self._apply_namespace(
            namespace,
            {
                "vector": vector,
                "top_k": top_k,
                "include_metadata": True,
                "filter": filter_dict,
            },
        )
        return index.query(**kwargs)

    def fetch_vector(self, index_type: str, vector_id: str):
        index, namespace = self._get_index_and_namespace(index_type)
        kwargs = self._apply_namespace(namespace, {"ids": [vector_id]})
        result = index.fetch(**kwargs)
        return result.vectors.get(vector_id)


pinecone_manager = PineconeManager()
