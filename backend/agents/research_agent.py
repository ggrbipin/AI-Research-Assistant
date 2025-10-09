"""
Research Agent: Retrieves relevant chunks from FAISS based on user query
"""
import numpy as np
from typing import List, Optional
from db.faiss_store import load_faiss_index
from db.multi_doc_store import multi_doc_store
from utils.embeddings import get_embedding
from utils.logger import agent_logger


class ResearchAgent:
    def __init__(self):
        self.name = "Research Agent"
        agent_logger.info(f"{self.name} initialized")

    def search(self, query: str, top_k: int = 5, source: str = None):
        """
        Search FAISS index for relevant document chunks

        Args:
            query: User's question
            top_k: Number of top results to return
            source: Optional document source filter

        Returns:
            dict with retrieved chunks and metadata
        """
        agent_logger.info(f"{self.name}: Starting search for query='{query}', top_k={top_k}, source={source}")

        index, metadata, documents = load_faiss_index()

        if index is None:
            agent_logger.error(f"{self.name}: No documents in database")
            return {
                "status": "error",
                "message": "No documents in database",
                "chunks": [],
                "sources": []
            }

        agent_logger.debug(f"{self.name}: Index loaded with {index.ntotal} vectors")

        # Get query embedding
        q_vec = np.array([get_embedding(query)]).astype("float32")
        agent_logger.debug(f"{self.name}: Query embedding generated")

        # Search more chunks if source filter is specified
        search_k = top_k * 10 if source else top_k
        agent_logger.debug(f"{self.name}: Searching for {search_k} chunks")
        distances, indices = index.search(q_vec, search_k)

        # Filter and collect results
        retrieved_chunks = []
        retrieved_sources = []

        for i in indices[0]:
            if i < len(metadata):
                chunk_data = metadata[i]

                # Apply source filter if specified
                if source is None or chunk_data.get("source") == source:
                    retrieved_chunks.append(chunk_data["chunk"])
                    retrieved_sources.append(chunk_data.get("source", "unknown"))

                    if len(retrieved_chunks) >= top_k:
                        break

        agent_logger.info(f"{self.name}: Retrieved {len(retrieved_chunks)} chunks from {len(set(retrieved_sources))} sources")

        return {
            "status": "success",
            "query": query,
            "chunks": retrieved_chunks,
            "sources": retrieved_sources,
            "num_results": len(retrieved_chunks)
        }

    def search_multi_doc(self, query: str, doc_ids: Optional[List[str]] = None, top_k: int = 5):
        """
        Search across selected documents using multi-doc store (Phase 5)

        Args:
            query: User's question
            doc_ids: List of document IDs to search (None or empty = all docs)
            top_k: Number of results to return

        Returns:
            dict with retrieved chunks and metadata
        """
        agent_logger.info(
            f"{self.name}: Multi-doc search for query='{query}', "
            f"doc_ids={doc_ids if doc_ids else 'ALL'}, top_k={top_k}"
        )

        # Check if any documents exist
        all_docs = multi_doc_store.list_documents()
        if not all_docs:
            agent_logger.error(f"{self.name}: No documents in multi-doc store")
            return {
                "status": "error",
                "message": "No documents in database",
                "chunks": [],
                "sources": []
            }

        agent_logger.debug(f"{self.name}: {len(all_docs)} documents available in multi-doc store")

        # If no doc_ids specified, search all documents
        if not doc_ids:
            doc_ids = [doc["doc_id"] for doc in all_docs]
            agent_logger.debug(f"{self.name}: Searching all {len(doc_ids)} documents")

        # Validate doc_ids exist
        available_doc_ids = {doc["doc_id"] for doc in all_docs}
        invalid_docs = [doc_id for doc_id in doc_ids if doc_id not in available_doc_ids]
        if invalid_docs:
            agent_logger.warning(f"{self.name}: Invalid document IDs: {invalid_docs}")
            doc_ids = [doc_id for doc_id in doc_ids if doc_id in available_doc_ids]
            if not doc_ids:
                return {
                    "status": "error",
                    "message": f"Invalid document IDs: {invalid_docs}",
                    "chunks": [],
                    "sources": []
                }

        # Get query embedding
        agent_logger.debug(f"{self.name}: Generating query embedding")
        q_vec = np.array(get_embedding(query))

        # Search selected documents
        agent_logger.debug(f"{self.name}: Searching {len(doc_ids)} document(s)")
        chunks, sources, distances = multi_doc_store.search_documents(
            doc_ids=doc_ids,
            query_vector=q_vec,
            top_k=top_k
        )

        agent_logger.info(
            f"{self.name}: Retrieved {len(chunks)} chunks from {len(set(sources))} sources | "
            f"Distance range: [{min(distances):.4f}, {max(distances):.4f}]" if distances else "No results"
        )

        return {
            "status": "success",
            "query": query,
            "chunks": chunks,
            "sources": sources,
            "distances": distances,
            "num_results": len(chunks),
            "searched_docs": doc_ids
        }
