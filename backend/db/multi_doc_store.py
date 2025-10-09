"""
Multi-Document FAISS Store
Manages separate FAISS indices for each document
Enables clean retrieval and context switching
"""
import os
import faiss
import numpy as np
import pickle
from typing import Dict, List, Optional, Tuple
from utils.logger import db_logger


class MultiDocumentStore:
    """
    Manages multiple FAISS indices, one per document
    """

    def __init__(self, base_path: str = "db/documents"):
        """
        Initialize multi-document store

        Args:
            base_path: Base directory for storing document indices
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        db_logger.info(f"Initialized MultiDocumentStore at: {base_path}")

    def _get_document_path(self, doc_id: str) -> str:
        """Get directory path for a specific document"""
        # Sanitize document ID for filesystem
        safe_doc_id = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in doc_id)
        return os.path.join(self.base_path, safe_doc_id)

    def save_document_index(
        self,
        doc_id: str,
        index: faiss.Index,
        metadata: List[Dict],
        doc_info: Dict
    ):
        """
        Save FAISS index for a specific document

        Args:
            doc_id: Document identifier (filename)
            index: FAISS index
            metadata: Chunk metadata
            doc_info: Document information (file_type, upload_date, etc.)
        """
        doc_path = self._get_document_path(doc_id)
        os.makedirs(doc_path, exist_ok=True)

        # Save FAISS index
        index_file = os.path.join(doc_path, "index.bin")
        faiss.write_index(index, index_file)

        # Save metadata
        meta_file = os.path.join(doc_path, "metadata.pkl")
        with open(meta_file, "wb") as f:
            pickle.dump(metadata, f)

        # Save document info
        info_file = os.path.join(doc_path, "info.pkl")
        with open(info_file, "wb") as f:
            pickle.dump(doc_info, f)

        db_logger.info(
            f"Saved document index: {doc_id} | "
            f"Vectors: {index.ntotal}, Chunks: {len(metadata)}"
        )

    def load_document_index(self, doc_id: str) -> Tuple[Optional[faiss.Index], List[Dict], Dict]:
        """
        Load FAISS index for a specific document

        Args:
            doc_id: Document identifier

        Returns:
            Tuple of (index, metadata, doc_info) or (None, [], {}) if not found
        """
        doc_path = self._get_document_path(doc_id)

        index_file = os.path.join(doc_path, "index.bin")
        meta_file = os.path.join(doc_path, "metadata.pkl")
        info_file = os.path.join(doc_path, "info.pkl")

        if not os.path.exists(index_file):
            db_logger.warning(f"Document index not found: {doc_id}")
            return None, [], {}

        # Load index
        index = faiss.read_index(index_file)

        # Load metadata
        with open(meta_file, "rb") as f:
            metadata = pickle.load(f)

        # Load document info
        with open(info_file, "rb") as f:
            doc_info = pickle.load(f)

        db_logger.debug(f"Loaded document index: {doc_id} | Vectors: {index.ntotal}")
        return index, metadata, doc_info

    def document_exists(self, doc_id: str) -> bool:
        """Check if document index exists"""
        doc_path = self._get_document_path(doc_id)
        index_file = os.path.join(doc_path, "index.bin")
        return os.path.exists(index_file)

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete document index

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        doc_path = self._get_document_path(doc_id)

        if not os.path.exists(doc_path):
            db_logger.warning(f"Cannot delete, document not found: {doc_id}")
            return False

        # Delete all files in document directory
        import shutil
        shutil.rmtree(doc_path)
        db_logger.info(f"Deleted document index: {doc_id}")
        return True

    def list_documents(self) -> List[Dict]:
        """
        List all stored documents

        Returns:
            List of document information dictionaries
        """
        documents = []

        if not os.path.exists(self.base_path):
            return documents

        for doc_dir in os.listdir(self.base_path):
            doc_path = os.path.join(self.base_path, doc_dir)
            info_file = os.path.join(doc_path, "info.pkl")

            if os.path.exists(info_file):
                with open(info_file, "rb") as f:
                    doc_info = pickle.load(f)

                # Add document ID
                doc_info["doc_id"] = doc_dir
                documents.append(doc_info)

        db_logger.debug(f"Listed {len(documents)} documents")
        return documents

    def search_documents(
        self,
        doc_ids: List[str],
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> Tuple[List[str], List[str], List[float]]:
        """
        Search across multiple documents

        Args:
            doc_ids: List of document IDs to search (empty = search all)
            query_vector: Query embedding vector
            top_k: Number of results to return

        Returns:
            Tuple of (chunks, sources, distances)
        """
        if not doc_ids:
            # Search all documents
            doc_ids = [doc["doc_id"] for doc in self.list_documents()]

        db_logger.debug(f"Searching {len(doc_ids)} document(s) for top {top_k} results")

        all_results = []  # List of (chunk, source, distance)

        for doc_id in doc_ids:
            index, metadata, doc_info = self.load_document_index(doc_id)

            if index is None:
                db_logger.warning(f"Skipping non-existent document: {doc_id}")
                continue

            # Ensure query_vector is 2D
            if len(query_vector.shape) == 1:
                query_vector = query_vector.reshape(1, -1)

            # Search this document's index
            distances, indices = index.search(query_vector.astype("float32"), min(top_k * 2, index.ntotal))

            # Collect results from this document
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(metadata):
                    chunk_data = metadata[idx]
                    all_results.append((
                        chunk_data["chunk"],
                        chunk_data.get("source", doc_id),
                        float(dist)
                    ))

        # Sort all results by distance (lower is better)
        all_results.sort(key=lambda x: x[2])

        # Take top k
        top_results = all_results[:top_k]

        chunks = [r[0] for r in top_results]
        sources = [r[1] for r in top_results]
        distances = [r[2] for r in top_results]

        db_logger.debug(f"Retrieved {len(chunks)} chunks from {len(set(sources))} sources")
        return chunks, sources, distances

    def get_document_stats(self, doc_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific document

        Args:
            doc_id: Document identifier

        Returns:
            Statistics dictionary or None if not found
        """
        index, metadata, doc_info = self.load_document_index(doc_id)

        if index is None:
            return None

        return {
            "doc_id": doc_id,
            "total_vectors": index.ntotal,
            "total_chunks": len(metadata),
            "dimension": index.d,
            "file_type": doc_info.get("file_type", "unknown"),
            "upload_date": doc_info.get("upload_date", "unknown"),
            "characters": doc_info.get("characters", 0)
        }

    def get_all_stats(self) -> Dict:
        """
        Get statistics for all documents

        Returns:
            Dictionary with overall statistics
        """
        documents = self.list_documents()

        total_vectors = 0
        total_chunks = 0

        for doc in documents:
            stats = self.get_document_stats(doc["doc_id"])
            if stats:
                total_vectors += stats["total_vectors"]
                total_chunks += stats["total_chunks"]

        return {
            "total_documents": len(documents),
            "total_vectors": total_vectors,
            "total_chunks": total_chunks,
            "documents": [self.get_document_stats(doc["doc_id"]) for doc in documents]
        }


# Global instance
multi_doc_store = MultiDocumentStore()
