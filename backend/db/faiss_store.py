import os
import faiss
import numpy as np
import pickle
from utils.logger import db_logger

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "db/faiss_index")
DOCUMENTS_PATH = os.getenv("VECTOR_DB_PATH", "db/faiss_index") + "_documents.pkl"

def save_faiss_index(index, metadata, documents=None):
    db_logger.info(f"Saving FAISS index: {index.ntotal} vectors, {len(metadata)} metadata entries")
    # Ensure directory exists
    os.makedirs(os.path.dirname(VECTOR_DB_PATH), exist_ok=True)

    faiss.write_index(index, VECTOR_DB_PATH + ".bin")
    db_logger.debug(f"FAISS index written to {VECTOR_DB_PATH}.bin")

    with open(VECTOR_DB_PATH + "_meta.pkl", "wb") as f:
        pickle.dump(metadata, f)
    db_logger.debug(f"Metadata written to {VECTOR_DB_PATH}_meta.pkl")

    # Save document list
    if documents is not None:
        with open(DOCUMENTS_PATH, "wb") as f:
            pickle.dump(documents, f)
        db_logger.debug(f"Document list saved: {len(documents)} documents")

    db_logger.info("FAISS index saved successfully")

def load_faiss_index():
    db_logger.debug("Loading FAISS index")
    if not os.path.exists(VECTOR_DB_PATH + ".bin"):
        db_logger.warning("No FAISS index found")
        return None, [], []

    index = faiss.read_index(VECTOR_DB_PATH + ".bin")
    db_logger.debug(f"Loaded FAISS index with {index.ntotal} vectors")

    with open(VECTOR_DB_PATH + "_meta.pkl", "rb") as f:
        metadata = pickle.load(f)
    db_logger.debug(f"Loaded {len(metadata)} metadata entries")

    # Load document list
    documents = []
    if os.path.exists(DOCUMENTS_PATH):
        with open(DOCUMENTS_PATH, "rb") as f:
            documents = pickle.load(f)
        db_logger.debug(f"Loaded {len(documents)} document names")

    db_logger.info(f"FAISS index loaded: {index.ntotal} vectors, {len(documents)} documents")
    return index, metadata, documents

def get_documents():
    """Get list of all uploaded documents"""
    db_logger.debug("Fetching document list")
    if os.path.exists(DOCUMENTS_PATH):
        with open(DOCUMENTS_PATH, "rb") as f:
            documents = pickle.load(f)
        db_logger.info(f"Retrieved {len(documents)} documents")
        return documents
    db_logger.warning("No documents file found")
    return []

def search_faiss(query_vector, top_k=5):
    """
    Search FAISS index with a query vector

    Args:
        query_vector: Numpy array of embedding vector
        top_k: Number of results to return

    Returns:
        List of text chunks
    """
    db_logger.info(f"Searching FAISS index for top {top_k} results")
    index, metadata, documents = load_faiss_index()

    if index is None:
        db_logger.warning("Cannot search: No FAISS index available")
        return []

    # Ensure query_vector is 2D array
    if len(query_vector.shape) == 1:
        query_vector = query_vector.reshape(1, -1)

    distances, indices = index.search(query_vector.astype('float32'), top_k)
    db_logger.debug(f"FAISS search completed, found {len(indices[0])} results")

    chunks = []
    for i in indices[0]:
        if i < len(metadata):
            chunks.append(metadata[i]["chunk"])

    db_logger.info(f"Retrieved {len(chunks)} chunks from FAISS index")
    return chunks
