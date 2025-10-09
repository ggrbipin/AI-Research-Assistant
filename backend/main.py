import os
from config import OPENAI_API_KEY
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from utils.document_parser import extract_text_from_file, chunk_text, SUPPORTED_EXTENSIONS
from utils.embeddings import get_embedding
from db.faiss_store import save_faiss_index, load_faiss_index, get_documents
from db.multi_doc_store import multi_doc_store
from db.sqlite_memory import conversation_memory
from models.schemas import AskRequest, SessionCreateResponse, SessionHistoryResponse
from openai import OpenAI
import faiss
import numpy as np
import tempfile
from fastapi.middleware.cors import CORSMiddleware
from agents.orchestrator import Orchestrator
from utils.logger import api_logger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
orchestrator = Orchestrator()

@app.get("/health")
def health():
    api_logger.info("Health check endpoint called")
    return {"status": "ok"}

@app.get("/documents")
def list_documents():
    """Get list of all uploaded documents (legacy + multi-doc)"""
    api_logger.info("Fetching list of documents")

    # Get legacy documents
    legacy_docs = get_documents()

    # Get multi-doc documents
    multi_docs = multi_doc_store.list_documents()

    # Combine and deduplicate
    all_docs = list(set(legacy_docs + [doc.get("original_filename", doc["doc_id"]) for doc in multi_docs]))

    api_logger.info(f"Retrieved {len(all_docs)} documents ({len(legacy_docs)} legacy, {len(multi_docs)} multi-doc)")
    return {
        "documents": all_docs,
        "multi_docs": multi_docs,
        "count": len(all_docs)
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), source: str = Form("document")):
    """
    Upload and index documents
    Supports: PDF, DOCX, HTML, TXT
    """
    # Get file extension
    filename = file.filename or "document"
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    api_logger.info(f"Upload request received: filename={filename}, extension={ext}, source={source}")

    # Validate file type
    if ext not in SUPPORTED_EXTENSIONS:
        api_logger.warning(f"Unsupported file format attempted: {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Save uploaded file temporarily
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file.write(await file.read())
    temp_file.close()

    api_logger.debug(f"Temporary file created: {temp_file.name}")

    try:
        # Extract text using unified parser
        api_logger.info(f"Extracting text from {file_type if 'file_type' in locals() else ext} file")
        text, file_type = extract_text_from_file(temp_file.name)
        api_logger.info(f"Text extraction successful: {len(text)} characters extracted")

        chunks = chunk_text(text)
        api_logger.info(f"Text chunked into {len(chunks)} chunks")

        if not chunks:
            api_logger.error("No chunks generated from file")
            raise HTTPException(status_code=400, detail="No text could be extracted from the file")

        # Generate embeddings
        api_logger.info(f"🔢 Generating embeddings for {len(chunks)} chunks")
        vectors = [get_embedding(c) for c in chunks]
        dim = len(vectors[0])
        api_logger.info(f"✅ All embeddings generated | Dimension: {dim}, Total vectors: {len(vectors)}")

        # Load or create FAISS index
        api_logger.info("Loading FAISS index")
        index, metadata, documents = load_faiss_index()
        if index is None:
            api_logger.info("Creating new FAISS index")
            index = faiss.IndexFlatL2(dim)
            metadata = []
            documents = []
        else:
            api_logger.info(f"Loaded existing index with {index.ntotal} vectors")

        # Track document names
        if source not in documents:
            documents.append(source)
            api_logger.info(f"Added new document to tracking: {source}")

        # Add vectors to index
        index.add(np.array(vectors).astype("float32"))
        metadata.extend([{"chunk": c, "source": source, "file_type": file_type} for c in chunks])
        api_logger.info(f"Added {len(chunks)} vectors to FAISS index")

        # Save updated index
        save_faiss_index(index, metadata, documents)
        api_logger.info(f"FAISS index saved successfully. Total vectors: {index.ntotal}")

        result = {
            "status": "uploaded",
            "chunks": len(chunks),
            "source": source,
            "file_type": file_type,
            "characters": len(text)
        }
        api_logger.info(f"Upload completed successfully: {result}")
        return result

    except ValueError as e:
        api_logger.error(f"ValueError during file processing: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        api_logger.error(f"Unexpected error during file processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
            api_logger.debug(f"Temporary file cleaned up: {temp_file.name}")


@app.post("/upload-v2")
async def upload_file_v2(file: UploadFile = File(...)):
    """
    Phase 5: Multi-document upload with separate FAISS indices
    Each document gets its own vector store for clean retrieval
    """
    filename = file.filename or "document"
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    api_logger.info(f"[Phase 5] Upload request: filename={filename}, extension={ext}")

    # Validate file type
    if ext not in SUPPORTED_EXTENSIONS:
        api_logger.warning(f"Unsupported file format: {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Save temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file.write(await file.read())
    temp_file.close()

    try:
        # Extract text
        api_logger.info(f"Extracting text from {ext} file")
        text, file_type = extract_text_from_file(temp_file.name)
        api_logger.info(f"Extracted {len(text)} characters")

        # Chunk text
        chunks = chunk_text(text)
        api_logger.info(f"Created {len(chunks)} chunks")

        if not chunks:
            raise HTTPException(status_code=400, detail="No text extracted")

        # Generate embeddings
        api_logger.info(f"🔢 Generating embeddings for {len(chunks)} chunks")
        vectors = [get_embedding(c) for c in chunks]
        dim = len(vectors[0])
        api_logger.info(f"✅ Embeddings generated | Dimension: {dim}")

        # Create FAISS index for this document
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(vectors).astype("float32"))

        # Create metadata
        metadata = [{"chunk": c, "source": filename, "file_type": file_type} for c in chunks]

        # Document info
        from datetime import datetime
        doc_info = {
            "original_filename": filename,
            "file_type": file_type,
            "upload_date": datetime.now().isoformat(),
            "characters": len(text),
            "chunks": len(chunks),
            "vectors": index.ntotal
        }

        # Save to multi-document store
        multi_doc_store.save_document_index(
            doc_id=filename,
            index=index,
            metadata=metadata,
            doc_info=doc_info
        )

        api_logger.info(f"✅ Document saved with separate index: {filename}")

        return {
            "status": "uploaded",
            "filename": filename,
            "file_type": file_type,
            "chunks": len(chunks),
            "characters": len(text),
            "vectors": index.ntotal,
            "storage_type": "multi-doc"
        }

    except ValueError as e:
        api_logger.error(f"ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        api_logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@app.post("/ask")
async def ask(req: AskRequest):
    api_logger.info(f"Query received: '{req.query}' (top_k={req.top_k}, source={req.source})")

    index, metadata, documents = load_faiss_index()
    if index is None:
        api_logger.warning("Query attempted with no documents available")
        raise HTTPException(status_code=400, detail="No documents available")

    api_logger.debug(f"Generating embedding for query")
    q_vec = np.array([get_embedding(req.query)]).astype("float32")

    # If source filter is specified, search more chunks to ensure we get enough matches
    search_k = req.top_k * 10 if req.source else req.top_k
    api_logger.debug(f"Searching FAISS index for top {search_k} chunks")
    distances, indices = index.search(q_vec, search_k)

    # Filter by source if specified
    retrieved = []
    sources = []
    for i in indices[0]:
        if i < len(metadata):
            chunk_data = metadata[i]
            # Apply source filter if specified
            if req.source is None or chunk_data["source"] == req.source:
                retrieved.append(chunk_data["chunk"])
                sources.append(chunk_data["source"])
                if len(retrieved) >= req.top_k:
                    break

    api_logger.info(f"Retrieved {len(retrieved)} chunks from {len(set(sources))} unique sources")

    if not retrieved:
        api_logger.warning(f"No content found for query with source filter: {req.source}")
        raise HTTPException(status_code=404, detail=f"No content found for document: {req.source}")

    context = "\n\n".join(retrieved)

    prompt = f"Answer using context below:\n{context}\n\nQuestion: {req.query}"
    model = os.getenv("LLM_MODEL", "gpt-4")
    api_logger.info(f"🤖 Invoking LLM - Model: {model}")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    # Log token usage
    usage = response.usage
    api_logger.info(
        f"✅ LLM Response received | "
        f"Tokens: {usage.prompt_tokens} input + {usage.completion_tokens} output = {usage.total_tokens} total"
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": sources[:req.top_k]
    }

@app.post("/ask-v2")
async def ask_multi_doc(req: AskRequest):
    """
    Phase 5: Multi-document query with context switching
    Query selected documents using multi-agent workflow
    """
    api_logger.info(f"[Phase 5] Multi-doc query: '{req.query}' (doc_ids={req.doc_ids}, session_id={req.session_id})")

    try:
        # Create or get session
        session_id = req.session_id
        if not session_id:
            session_id = conversation_memory.create_session()
        elif not conversation_memory.session_exists(session_id):
            conversation_memory.create_session(session_id)

        api_logger.debug(f"Session: {session_id}")

        # Add user message to history
        conversation_memory.add_message(session_id, "user", req.query)

        # Get conversation context
        context_history = conversation_memory.get_context(session_id, max_messages=10)

        # Process query with multi-doc agents
        api_logger.info("Starting multi-doc agent workflow")
        result = orchestrator.process_query_multi_doc(
            query=req.query,
            doc_ids=req.doc_ids,
            top_k=req.top_k,
            conversation_context=context_history
        )

        if result["status"] == "error":
            api_logger.error(f"Multi-doc workflow error: {result['answer']}")
            raise HTTPException(status_code=400, detail=result["answer"])

        api_logger.info("Multi-doc workflow completed successfully")

        # Add assistant response to history
        conversation_memory.add_message(
            session_id,
            "assistant",
            result["answer"],
            metadata={
                "sources": result.get("sources", []),
                "workflow_log": result.get("workflow_log", []),
                "searched_docs": result.get("searched_docs", [])
            }
        )

        return {
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "workflow_log": result.get("workflow_log", []),
            "metadata": result.get("metadata", {}),
            "searched_docs": result.get("searched_docs", []),
            "session_id": session_id
        }

    except Exception as e:
        api_logger.error(f"Error in multi-doc workflow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in multi-doc workflow: {str(e)}")


@app.post("/ask-agents")
async def ask_with_agents(req: AskRequest):
    """
    Answer query using multi-agent workflow with conversation memory:
    Research Agent → Summarizer Agent → Critic Agent → Editor Agent
    """
    api_logger.info(f"Multi-agent query received: '{req.query}' (session_id={req.session_id})")

    try:
        # Create or get session
        session_id = req.session_id
        if not session_id:
            session_id = conversation_memory.create_session()
        elif not conversation_memory.session_exists(session_id):
            conversation_memory.create_session(session_id)

        api_logger.debug(f"Session: {session_id}")

        # Add user message to history
        conversation_memory.add_message(session_id, "user", req.query)
        api_logger.debug(f"Added user message to session {session_id}")

        # Get conversation context
        context_history = conversation_memory.get_context(session_id, max_messages=10)
        api_logger.debug(f"Retrieved conversation context (length: {len(context_history)} chars)")

        # Process query with agents
        api_logger.info("Starting multi-agent workflow")
        result = orchestrator.process_query(
            query=req.query,
            top_k=req.top_k,
            source=req.source,
            conversation_context=context_history
        )

        if result["status"] == "error":
            api_logger.error(f"Multi-agent workflow returned error: {result['answer']}")
            raise HTTPException(status_code=400, detail=result["answer"])

        api_logger.info("Multi-agent workflow completed successfully")

        # Add assistant response to history
        conversation_memory.add_message(
            session_id,
            "assistant",
            result["answer"],
            metadata={
                "sources": result.get("sources", []),
                "workflow_log": result.get("workflow_log", [])
            }
        )
        api_logger.debug(f"Added assistant response to session {session_id}")

        return {
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "workflow_log": result.get("workflow_log", []),
            "metadata": result.get("metadata", {}),
            "session_id": session_id
        }

    except Exception as e:
        api_logger.error(f"Error in multi-agent workflow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in multi-agent workflow: {str(e)}")


# Session Management Endpoints

@app.post("/sessions/create", response_model=SessionCreateResponse)
def create_session():
    """Create a new conversation session"""
    api_logger.info("Creating new session")
    session_id = conversation_memory.create_session()
    metadata = conversation_memory.get_session_metadata(session_id)
    api_logger.info(f"Session created: {session_id}")
    return {
        "session_id": session_id,
        "created_at": metadata["created_at"]
    }


@app.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
def get_session_history(session_id: str):
    """Get conversation history for a session"""
    api_logger.info(f"Fetching history for session: {session_id}")
    if not conversation_memory.session_exists(session_id):
        api_logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    messages = conversation_memory.get_history(session_id)
    metadata = conversation_memory.get_session_metadata(session_id)
    api_logger.info(f"Retrieved {len(messages)} messages for session {session_id}")

    return {
        "session_id": session_id,
        "messages": messages,
        "metadata": metadata
    }


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    """Clear conversation history for a session"""
    api_logger.info(f"Clearing session: {session_id}")
    if not conversation_memory.session_exists(session_id):
        api_logger.warning(f"Attempted to clear non-existent session: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_memory.clear_session(session_id)
    api_logger.info(f"Session cleared: {session_id}")
    return {"status": "cleared", "session_id": session_id}


@app.get("/sessions")
def list_sessions():
    """Get list of all active sessions"""
    api_logger.info("Fetching all sessions")
    sessions = conversation_memory.get_all_sessions()
    api_logger.info(f"Retrieved {len(sessions)} active sessions")
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/workflow/diagram")
def get_workflow_diagram():
    """Get LangGraph workflow visualization as Mermaid diagram"""
    api_logger.info("Generating workflow diagram")
    diagram = orchestrator.get_workflow_diagram()
    api_logger.debug(f"Diagram generated (length: {len(diagram)} chars)")
    return {
        "diagram": diagram,
        "format": "mermaid",
        "description": "Multi-agent workflow with conditional routing"
    }


@app.get("/stats")
def get_database_stats():
    """Get database statistics"""
    api_logger.info("Fetching database statistics")

    # Conversation stats
    conversation_stats = conversation_memory.get_stats()

    # FAISS stats
    index, metadata, documents = load_faiss_index()
    faiss_stats = {
        "total_vectors": index.ntotal if index else 0,
        "total_documents": len(documents),
        "total_chunks": len(metadata)
    }

    stats = {
        "conversations": conversation_stats,
        "documents": faiss_stats
    }

    api_logger.info(f"Database stats retrieved: {stats}")
    return stats
