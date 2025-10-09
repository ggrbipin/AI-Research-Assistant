import { useState, useEffect, useRef } from "react";
import axios from "axios";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Document {
  doc_id: string;
  original_filename: string;
  file_type: string;
  upload_date: string;
  chunks: number;
}

export default function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]); // Multi-select: array of doc IDs
  const [showMultiSelect, setShowMultiSelect] = useState(false); // Toggle for advanced mode
  const [useAgents, setUseAgents] = useState(true);
  const [workflowLog, setWorkflowLog] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAgent, setCurrentAgent] = useState("");
  const [sessionId, setSessionId] = useState<string>(""); // Track conversation session
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchDocuments = async () => {
    try {
      const res = await axios.get("http://localhost:8000/documents");
      const multiDocs = res.data.multi_docs || [];
      setDocuments(multiDocs);

      // Auto-select all documents by default
      if (multiDocs.length > 0 && selectedDocIds.length === 0) {
        setSelectedDocIds(multiDocs.map((doc: Document) => doc.doc_id));
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    }
  };

  const toggleDocSelection = (docId: string) => {
    setSelectedDocIds(prev =>
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  const selectAllDocs = () => {
    setSelectedDocIds(documents.map(doc => doc.doc_id));
  };

  const deselectAllDocs = () => {
    setSelectedDocIds([]);
  };

  const startNewConversation = () => {
    setMessages([]);
    setSessionId("");
    setWorkflowLog([]);
    setInput("");
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadStatus("Uploading...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:8000/upload-v2", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setUploadStatus(`✓ Uploaded: ${res.data.chunks} chunks indexed`);
      await fetchDocuments();

      // Auto-select the newly uploaded document
      if (res.data.filename) {
        setSelectedDocIds(prev => [...prev, res.data.filename]);
      }

      setTimeout(() => setUploadStatus(""), 3000);
    } catch (err) {
      console.error(err);
      setUploadStatus("✗ Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isProcessing) return;

    const userMessage: Message = { role: "user", content: input };
    const currentQuery = input;

    setInput("");
    setMessages((prev) => [...prev, userMessage]);
    setIsProcessing(true);
    setWorkflowLog([]);
    setCurrentAgent(useAgents ? "Initializing multi-agent workflow..." : "Processing your query...");

    try {
      let endpoint: string;
      let payload: any;

      if (useAgents) {
        // Use multi-doc endpoint with agents
        endpoint = "http://localhost:8000/ask-v2";
        payload = {
          query: currentQuery,
          top_k: 5,
          doc_ids: selectedDocIds.length > 0 ? selectedDocIds : null, // Array of selected doc IDs
          session_id: sessionId || undefined
        };
      } else {
        // Simple RAG without agents (legacy)
        endpoint = "http://localhost:8000/ask";
        payload = {
          query: currentQuery,
          top_k: 5,
          source: selectedDocIds.length === 1 ? selectedDocIds[0] : null
        };
      }

      if (useAgents) {
        setCurrentAgent("[1/4] Research Agent: Searching database...");
        await new Promise(resolve => setTimeout(resolve, 300));
      }

      const res = await axios.post(endpoint, payload);

      if (useAgents && res.data.workflow_log) {
        setWorkflowLog(res.data.workflow_log);
      }

      // Store session ID for follow-up queries
      if (res.data.session_id && !sessionId) {
        setSessionId(res.data.session_id);
      }

      const assistantMessage: Message = {
        role: "assistant",
        content: res.data.answer
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentAgent("");
    } catch (err: any) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || "Error contacting backend.";
      const errorMessage: Message = { role: "assistant", content: errorMsg };
      setMessages((prev) => [...prev, errorMessage]);
      setCurrentAgent("");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  AI Research Assistant
                </h1>
                <p className="text-sm text-gray-500">Intelligent Document Q&A System</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {sessionId && (
                <button
                  onClick={startNewConversation}
                  className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg text-sm font-medium shadow-sm hover:shadow-md transition-all duration-200 flex items-center space-x-2"
                  title="Start a new conversation"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span>New Chat</span>
                </button>
              )}
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                documents.length > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {documents.length} Document{documents.length !== 1 ? 's' : ''}
              </span>
              {sessionId && (
                <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700" title={`Session: ${sessionId}`}>
                  🧠 Memory Active
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">

            {/* Upload Card */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload Document
              </h3>

              <label className="block">
                <div className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all
                  ${uploading ? 'border-gray-300 bg-gray-50' : 'border-blue-300 hover:border-blue-500 hover:bg-blue-50'}`}>
                  <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm text-gray-600 font-medium">
                    {uploading ? 'Uploading...' : 'Click to upload document'}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">PDF, DOCX, HTML, or TXT</p>
                  <input
                    type="file"
                    accept=".pdf,.docx,.html,.htm,.txt"
                    onChange={handleFileUpload}
                    disabled={uploading}
                    className="hidden"
                  />
                </div>
              </label>

              {uploadStatus && (
                <div className={`mt-4 p-3 rounded-lg text-sm font-medium animate-slide-up ${
                  uploadStatus.startsWith("✓")
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {uploadStatus}
                </div>
              )}
            </div>

            {/* Document Selector - Hybrid UI */}
            {documents.length > 0 && (
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-800 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Select Documents
                  </h3>
                  <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded">
                    {selectedDocIds.length}/{documents.length}
                  </span>
                </div>

                {/* Simple Mode: Dropdown */}
                {!showMultiSelect && (
                  <div className="space-y-3">
                    <select
                      value={selectedDocIds.length === documents.length ? 'all' : selectedDocIds.length > 1 ? 'custom' : selectedDocIds[0] || ''}
                      onChange={(e) => {
                        if (e.target.value === 'all') {
                          selectAllDocs();
                        } else if (e.target.value !== 'custom') {
                          setSelectedDocIds([e.target.value]);
                        }
                      }}
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-sm font-medium transition-all"
                    >
                      <option value="all">🌐 All Documents ({documents.length})</option>
                      {selectedDocIds.length > 1 && selectedDocIds.length < documents.length && (
                        <option value="custom">📚 Custom Selection ({selectedDocIds.length} documents)</option>
                      )}
                      {documents.map((doc) => (
                        <option key={doc.doc_id} value={doc.doc_id}>
                          📄 {doc.original_filename}
                        </option>
                      ))}
                    </select>

                    {/* Selected Document Info */}
                    {selectedDocIds.length === documents.length ? (
                      <div className="p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200">
                        <div className="flex items-center justify-between">
                          <div className="text-xs font-semibold text-green-800">
                            ✓ Searching across all {documents.length} documents
                          </div>
                          <div className="text-xs text-green-600">
                            {documents.reduce((sum, doc) => sum + doc.chunks, 0)} total chunks
                          </div>
                        </div>
                      </div>
                    ) : selectedDocIds.length === 1 ? (
                      <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                        {documents.find(d => d.doc_id === selectedDocIds[0]) && (
                          <div className="text-xs text-blue-800">
                            <div className="font-medium truncate">
                              📄 {documents.find(d => d.doc_id === selectedDocIds[0])?.original_filename}
                            </div>
                            <div className="text-blue-600 mt-1">
                              {documents.find(d => d.doc_id === selectedDocIds[0])?.file_type.toUpperCase()} • {documents.find(d => d.doc_id === selectedDocIds[0])?.chunks} chunks
                            </div>
                          </div>
                        )}
                      </div>
                    ) : selectedDocIds.length > 1 ? (
                      <div className="p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
                        <div className="text-xs font-semibold text-purple-800 mb-2">
                          📚 Custom Selection ({selectedDocIds.length} documents)
                        </div>
                        <div className="text-xs text-purple-700 space-y-1">
                          {selectedDocIds.slice(0, 3).map((docId) => {
                            const doc = documents.find(d => d.doc_id === docId);
                            return doc ? (
                              <div key={docId} className="truncate">• {doc.original_filename}</div>
                            ) : null;
                          })}
                          {selectedDocIds.length > 3 && (
                            <div className="text-purple-600 font-medium">+ {selectedDocIds.length - 3} more...</div>
                          )}
                        </div>
                      </div>
                    ) : null}

                    {/* Toggle to Advanced Mode */}
                    <button
                      onClick={() => setShowMultiSelect(true)}
                      className="w-full px-4 py-2.5 text-sm font-medium text-indigo-600 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg hover:from-indigo-100 hover:to-purple-100 transition-all duration-200 flex items-center justify-center gap-2 shadow-sm hover:shadow"
                      title="Choose specific documents to search"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                      </svg>
                      <span>Select Specific Documents</span>
                    </button>
                  </div>
                )}

                {/* Advanced Mode: Multi-Select Checkboxes */}
                {showMultiSelect && (
                  <div className="space-y-3">
                    {/* Mode Indicator + Back Button */}
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-200">
                      <div className="text-xs font-medium text-gray-600 flex items-center gap-2">
                        <svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                        </svg>
                        Multi-Select Mode
                      </div>
                      <button
                        onClick={() => setShowMultiSelect(false)}
                        className="px-3 py-1 text-xs font-medium text-indigo-600 bg-white border border-indigo-200 rounded hover:bg-indigo-50 transition-colors flex items-center gap-1"
                        title="Return to simple mode"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Back
                      </button>
                    </div>

                    {/* Selection Summary */}
                    <div className="p-2 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
                      <div className="text-xs font-semibold text-purple-800">
                        {selectedDocIds.length === 0 ? (
                          <span>⚠️ No documents selected - Please select at least one</span>
                        ) : selectedDocIds.length === documents.length ? (
                          <span>🌐 All {documents.length} documents selected</span>
                        ) : (
                          <span>📚 {selectedDocIds.length} of {documents.length} documents selected</span>
                        )}
                      </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="flex gap-2">
                      <button
                        onClick={selectAllDocs}
                        className="flex-1 px-3 py-2 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                      >
                        ✓ All
                      </button>
                      <button
                        onClick={deselectAllDocs}
                        className="flex-1 px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        ✗ None
                      </button>
                    </div>

                    {/* Document Checkboxes */}
                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                      {documents.map((doc) => (
                        <label
                          key={doc.doc_id}
                          className={`flex items-start p-3 rounded-lg border-2 cursor-pointer transition-all duration-150 ${
                            selectedDocIds.includes(doc.doc_id)
                              ? 'border-blue-500 bg-blue-50 shadow-sm'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50 bg-white'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedDocIds.includes(doc.doc_id)}
                            onChange={() => toggleDocSelection(doc.doc_id)}
                            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 mt-0.5 flex-shrink-0"
                          />
                          <div className="ml-3 flex-1 min-w-0">
                            <div className="text-sm font-medium text-gray-800 truncate">
                              📄 {doc.original_filename}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {doc.file_type.toUpperCase()} • {doc.chunks} chunks
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Agent Settings */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </h3>

              <div className="flex items-center space-x-3 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                <input
                  type="checkbox"
                  id="use-agents"
                  checked={useAgents}
                  onChange={(e) => setUseAgents(e.target.checked)}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <label htmlFor="use-agents" className="flex-1 cursor-pointer">
                  <div className="font-medium text-gray-800">Multi-Agent Mode</div>
                  <div className="text-xs text-gray-600">Research → Summarize → Critique → Edit</div>
                </label>
              </div>

              {/* Workflow Log */}
              {useAgents && workflowLog.length > 0 && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="text-xs font-semibold text-blue-800 mb-2">Workflow Progress:</div>
                  {workflowLog.map((log, idx) => (
                    <div key={idx} className="text-xs text-blue-700 py-1 flex items-start">
                      <span className="text-blue-500 mr-2">•</span>
                      {log}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Main Chat Area */}
          <div className="lg:col-span-2">
            <div className="card h-[calc(100vh-120px)] flex flex-col">

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-16">
                    <div className="w-24 h-24 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-full mx-auto mb-5 flex items-center justify-center shadow-sm">
                      <svg className="w-12 h-12 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-bold text-gray-800 mb-2">Start a Conversation</h3>
                    <p className="text-gray-600 text-sm mb-4">Upload a document and ask questions to start chat</p>
                  </div>
                )}

                {messages.map((m, idx) => (
                  <div key={idx} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] ${
                      m.role === "user"
                        ? "chat-message chat-message-user"
                        : "chat-message chat-message-assistant"
                    }`}>
                      <div className="flex items-center mb-2">
                        {m.role === "assistant" && (
                          <div className="w-6 h-6 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full mr-2 flex items-center justify-center">
                            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                            </svg>
                          </div>
                        )}
                        <span className={`text-sm font-semibold ${
                          m.role === "user" ? "text-white" : "text-gray-700"
                        }`}>
                          {m.role === "user" ? "You" : "AI Assistant"}
                        </span>
                      </div>
                      <div className={`text-sm leading-relaxed ${
                        m.role === "user" ? "text-white" : "text-gray-800"
                      }`}>
                        {m.content}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Processing Indicator */}
                {isProcessing && (
                  <div className="flex justify-start">
                    <div className="max-w-[80%] bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg p-4 shadow-sm border border-orange-200 animate-pulse">
                      <div className="flex items-center mb-2">
                        <div className="flex space-x-1 mr-3">
                          <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                          <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                        </div>
                        <span className="text-sm font-semibold text-orange-700">AI is thinking...</span>
                      </div>
                      <div className="text-xs text-orange-600 italic">
                        {currentAgent || "Processing your request..."}
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t border-gray-200 p-4 bg-gray-50">
                <div className="flex space-x-3">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !isProcessing) sendMessage(); }}
                    disabled={isProcessing}
                    placeholder={isProcessing ? "Processing..." : "Type your question..."}
                    className="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed transition-all"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isProcessing || !input.trim()}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <span>Send</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
