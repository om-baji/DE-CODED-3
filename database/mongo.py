from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from settings import MONGO_URL, DB_NAME
from utils.logger import get_logger

logger = get_logger(__name__)


class MongoManager:
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        logger.info(f"Connected to MongoDB: {MONGO_URL}/{DB_NAME}")


    def _get_collection(self, collection_name: str):
        if not collection_name:
            raise ValueError("Collection name cannot be empty")
        return self.db[collection_name]

    def _log_error(self, operation: str, error: Exception):
        logger.error(f"MongoDB {operation} failed: {str(error)}")

    def insert_one(self, collection_name: str, document: dict):
        try:
            collection = self._get_collection(collection_name)
            result = collection.insert_one(document)
            logger.info(f"Inserted document into '{collection_name}' with _id={result.inserted_id}")
            return result.inserted_id
        except PyMongoError as e:
            self._log_error("insert_one", e)
            return None

    def insert_many(self, collection_name: str, documents: list[dict]):
        try:
            collection = self._get_collection(collection_name)
            result = collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} documents into '{collection_name}'")
            return result.inserted_ids
        except PyMongoError as e:
            self._log_error("insert_many", e)
            return []

    def find_one(self, collection_name: str, query: dict, projection: dict = None):
        try:
            collection = self._get_collection(collection_name)
            return collection.find_one(query, projection)
        except PyMongoError as e:
            self._log_error("find_one", e)
            return None

    def find_many(self, collection_name: str, query: dict = None, projection: dict = None, limit: int = 100):
        try:
            collection = self._get_collection(collection_name)
            cursor = collection.find(query or {}, projection).limit(limit)
            return list(cursor)
        except PyMongoError as e:
            self._log_error("find_many", e)
            return []

    def update_one(self, collection_name: str, query: dict, update_data: dict, upsert: bool = False):
        try:
            collection = self._get_collection(collection_name)
            result = collection.update_one(query, {"$set": update_data}, upsert=upsert)
            logger.info(f"Updated {result.modified_count} document(s) in '{collection_name}'")
            return result.modified_count
        except PyMongoError as e:
            self._log_error("update_one", e)
            return 0

    def delete_one(self, collection_name: str, query: dict):
        try:
            collection = self._get_collection(collection_name)
            result = collection.delete_one(query)
            logger.info(f"Deleted {result.deleted_count} document(s) from '{collection_name}'")
            return result.deleted_count
        except PyMongoError as e:
            self._log_error("delete_one", e)
            return 0

    def ensure_index(self, collection_name: str, field_name: str, ascending: bool = True, unique: bool = False):
        try:
            collection = self._get_collection(collection_name)
            order = ASCENDING if ascending else DESCENDING
            collection.create_index([(field_name, order)], unique=unique)
            logger.info(f"Index ensured on '{field_name}' (unique={unique}) in '{collection_name}'")
        except PyMongoError as e:
            self._log_error("ensure_index", e)

    def aggregate(self, collection_name: str, pipeline: list[dict]):
        try:
            collection = self._get_collection(collection_name)
            results = list(collection.aggregate(pipeline))
            logger.debug(f"Aggregation pipeline executed on '{collection_name}'")
            return results
        except PyMongoError as e:
            self._log_error("aggregate", e)
            return []

    def count_documents(self, collection_name: str, query: dict = None):
        try:
            collection = self._get_collection(collection_name)
            count = collection.count_documents(query or {})
            logger.debug(f"Counted {count} document(s) in '{collection_name}'")
            return count
        except PyMongoError as e:
            self._log_error("count_documents", e)
            return 0

    def drop_collection(self, collection_name: str):
        try:
            self.db.drop_collection(collection_name)
            logger.warning(f"Collection '{collection_name}' dropped")
        except PyMongoError as e:
            self._log_error("drop_collection", e)

    def list_collections(self):
        try:
            return self.db.list_collection_names()
        except PyMongoError as e:
            self._log_error("list_collections", e)
            return []


# Global instance
mongo_manager = MongoManager()
