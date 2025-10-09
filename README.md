# 🤖 AI Research Assistant with Multi-Agent Collaboration

An AI-powered **Multi-Agent Research Assistant** built with **Generative AI, Agentic AI, LangGraph, RAG, Persistent Memory, FAISS, and FastAPI**. It supports multi-format uploads, intelligent PDF analysis, and expert-like Q&A via Researcher, Summarizer, Critic, and Editor agents - offering deep, contextual, and interactive research insights.

This **Multi-Agent architecture** (Researcher, Summarizer, Critic, and Editor) simulates how real researchers process information. It integrates **FastAPI (backend), Next.js + TailwindCSS (frontend), FAISS (vector search), and SQLite** for conversation persistence.

## 🚀 Features

- 🧠 **Multi-Agent Workflow**
  - **Research Agent →** Finds relevant chunks using FAISS
  - **Summarizer Agent →** Creates concise summaries
  - **Critic Agent →** Identifies limitations and gaps
  - **Editor Agent →** Refines and formats final responses
- **📚 Multi-Document Support** → Upload and query multiple PDFs, DOCX, or TXT files
- **💬 Conversation Memory** → SQLite-backed memory for contextual, follow-up queries
- **⚡ FAISS Vector Search** → High-speed semantic retrieval of embedded text chunks
- **🔄 LangGraph Orchestration** → Structured multi-agent pipeline with conditional routing
- **🎨 Modern UI** → Responsive frontend built with Next.js and TailwindCSS

## 🏗️ Project Structure

```
AI-Research-Assistant/
├── backend/                           # FastAPI Backend
│   ├── agents/                        # Multi-Agent System
│   │   ├── __init__.py
│   │   ├── agent_state.py            # Shared state for LangGraph
│   │   ├── critic_agent.py           # Validates response quality
│   │   ├── editor_agent.py           # Refines final output
│   │   ├── langgraph_nodes.py        # LangGraph node definitions
│   │   ├── langgraph_workflow.py     # Workflow graph construction
│   │   ├── orchestrator.py           # Main workflow orchestrator
│   │   ├── research_agent.py         # Document retrieval agent
│   │   └── summarizer_agent.py       # Summarization agent
│   │
│   ├── db/                            # Database & Storage
│   │   ├── conversation_memory.py    # Legacy memory (deprecated)
│   │   ├── conversations.db          # SQLite database
│   │   ├── faiss_index.bin           # FAISS vector index
│   │   ├── faiss_index_documents.pkl # Document metadata
│   │   ├── faiss_index_meta.pkl      # Chunk metadata
│   │   ├── faiss_store.py            # FAISS operations
│   │   ├── memory_store.py           # Legacy memory store
│   │   ├── multi_doc_store.py        # Multi-document FAISS manager
│   │   ├── sqlite_memory.py          # SQLite conversation memory
│   │   └── documents/                # Per-document FAISS indexes
│   │       └── [doc_name]/           # Individual document stores
│   │           ├── index.bin
│   │           ├── metadata.pkl
│   │           └── info.pkl
│   │
│   ├── logs/                          # Application Logs
│   │   ├── agents.log                # Agent workflow logs
│   │   ├── api.log                   # API request logs
│   │   ├── database.log              # Database operation logs
│   │   └── parser.log                # Document parsing logs
│   │
│   ├── models/                        # Data Models
│   │   └── schemas.py                # Pydantic request/response schemas
│   │
│   ├── utils/                         # Utility Modules
│   │   ├── document_parser.py        # Multi-format document parser
│   │   ├── embeddings.py             # OpenAI embedding generation
│   │   ├── logger.py                 # Logging configuration
│   │   └── pdf_parser.py             # Legacy PDF parser
│   │
│   ├── config.py                      # Configuration loader
│   ├── main.py                        # FastAPI application & routes
│   └── requirements.txt               # Python dependencies
│
├── frontend/                          # Next.js Frontend
│   ├── components/                    # React Components
│   │   ├── AgentGraph.tsx            # Workflow visualization
│   │   └── ChatBox.tsx               # Chat interface
│   │
│   ├── pages/                         # Next.js Pages
│   │   ├── _app.tsx                  # App wrapper with providers
│   │   ├── index.tsx                 # Main chat interface
│   │   └── history.tsx               # Conversation history view
│   │
│   ├── styles/                        # Stylesheets
│   │   └── globals.css               # Global TailwindCSS styles
│   │
│   ├── next-env.d.ts                 # Next.js TypeScript declarations
│   ├── package.json                  # Node dependencies
│   ├── package-lock.json             # Lockfile
│   ├── postcss.config.js             # PostCSS configuration
│   ├── tailwind.config.js            # TailwindCSS configuration
│   └── tsconfig.json                 # TypeScript configuration
│
├── venv/                              # Python Virtual Environment
│
├── .env                               # Environment variables (gitignored)
├── .gitignore                         # Git ignore rules
├── PROJECT_ANALYSIS.md                # Project documentation
└── README.md                          # This file
```

## ⚙️ Tech Stack

### Backend
- **FastAPI**: High-performance async API framework
- **LangGraph**: Agent workflow orchestration
- **OpenAI**: GPT-4 and text-embedding-3-small models
- **FAISS**: Vector similarity search (CPU)
- **SQLite**: Conversation memory persistence
- **PDFPlumber**: PDF text extraction
- **Python-DOCX**: DOCX parsing
- **BeautifulSoup4**: HTML parsing

### Frontend
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe development
- **TailwindCSS 4**: Utility-first styling
- **React Query (TanStack)**: Data fetching and caching
- **Radix UI**: Accessible component primitives
- **Axios**: HTTP client

## 🔧 Prerequisites

- Python 3.8+
- Node.js 18+
- OpenAI API Key

## ⚡ Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/divyeshmutha12/AI-Research-Assistant.git
cd AI-Research-Assistant
```

### 2️⃣ Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3️⃣ Environment Configuration

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key
VECTOR_DB_PATH=./backend/db/documents
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
BACKEND_PORT=8000
```

### 4️⃣ Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## 🧩 API Endpoints

### Document Management
- `POST /upload` - Upload document (legacy, single FAISS index)
- `POST /upload-v2` - Upload document (multi-doc, separate indexes)
- `GET /documents` - List all uploaded documents

### Query Endpoints
- `POST /ask` - Simple RAG query (legacy)
- `POST /ask-agents` - Multi-agent workflow query (single FAISS index)
- `POST /ask-v2` - Multi-document query with context switching

### Session Management
- `POST /sessions/create` - Create new conversation session
- `GET /sessions/{session_id}/history` - Get session history
- `DELETE /sessions/{session_id}` - Clear session
- `GET /sessions` - List all sessions

### Utilities
- `GET /health` - Health check
- `GET /workflow/diagram` - Get LangGraph workflow as Mermaid diagram
- `GET /stats` - Database statistics

## 🧠 Multi-Agent Workflow

The system uses a sophisticated multi-agent pipeline:

1. **Research Agent**: Searches documents using FAISS similarity search
2. **Summarizer Agent**: Condenses retrieved information
3. **Critic Agent**: Evaluates quality and completeness
4. **Editor Agent**: Produces final polished response

Agents communicate through a shared state managed by LangGraph, with conditional routing based on response quality.

## 🧾 Document Processing

Supported formats:
- **PDF**: Extracted using PDFPlumber
- **DOCX**: Parsed with python-docx
- **HTML**: Cleaned with BeautifulSoup4
- **TXT**: Direct text reading

Documents are:
1. Chunked into ~500 character segments
2. Embedded using OpenAI's text-embedding-3-small
3. Stored in FAISS vector indexes
4. Retrieved via semantic similarity search

## 💬 Conversation Memory

- **Session-based**: Each conversation has a unique session ID
- **SQLite storage**: Persistent chat history
- **Context retention**: Previous messages inform agent responses
- **Metadata tracking**: Sources and workflow logs stored per message

## Development

### Backend Structure

```python
# Example: Adding a new agent
from agents.base import BaseAgent

class NewAgent(BaseAgent):
    def process(self, state):
        # Agent logic here
        return updated_state
```

### Frontend Structure

```tsx
// Example: API call with React Query
const { data } = useQuery({
  queryKey: ['documents'],
  queryFn: async () => {
    const res = await axios.get('http://localhost:8000/documents')
    return res.data
  }
})
```

## 📜 Logging

Comprehensive logging across:
- API requests (`backend/logs/api.log`)
- Agent workflows (`backend/logs/agents.log`)
- Document parsing (`backend/logs/parser.log`)
- Database operations (`backend/logs/database.log`)

## 🌟 Future Scope

- LangSmith integration for agent evaluation
- Audio/video research input (Whisper API)
- Multi-language summarization
- Graph visualization of LangGraph workflow
- PDF/Word export for AI-generated reports

## 🪪 License

**MIT License** – Free to use and modify.


