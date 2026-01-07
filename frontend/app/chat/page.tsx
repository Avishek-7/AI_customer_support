"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ChatBubble from "./../../components/ChatBubble";
import ChatInput from "./../../components/ChatInput";
import UploadModal from "./../../components/UploadModal";
import { chatLogger } from "@/lib/logger";

type Source = { title?: string; document_id?: number; chunk_id?: number };

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

type DocumentItem = { id: number; title: string };

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const chatRef = useRef<HTMLDivElement>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  // Get token - only available on client side
  const getToken = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  };

  // Fetch documents
  const fetchDocs = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    chatLogger.debug("Fetching documents for sidebar");
    const res = await fetch(`${API_BASE}/documents/`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    // If unauthorized, clear token and redirect to login
    if (res.status === 401) {
      chatLogger.warn("Token expired or invalid, redirecting to login");
      localStorage.removeItem("token");
      window.location.href = "/login";
      return;
    }

    const data = await res.json();
    chatLogger.info("Documents loaded", { count: data.documents?.length || 0 });
    setDocs(data.documents ?? []);
  }, []);

  // Delete selected documents
  const handleDeleteSelected = async () => {
    const token = getToken();
    if (!token || selectedDocIds.length === 0) return;

    if (!confirm(`Delete ${selectedDocIds.length} document(s)? This cannot be undone.`)) return;

    chatLogger.info("Deleting documents", { documentIds: selectedDocIds });
    try {
      // Delete each selected document
      await Promise.all(
        selectedDocIds.map((id) =>
          fetch(`${API_BASE}/documents/${id}`, {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      chatLogger.info("Documents deleted successfully", { count: selectedDocIds.length });
      // Clear selection and refresh list
      setSelectedDocIds([]);
      await fetchDocs();
    } catch (err) {
      chatLogger.error("Failed to delete documents", { error: String(err) });
      console.error("Failed to delete documents:", err);
    }
  };

  // Check authentication and fetch documents on mount
  useEffect(() => {
    const token = getToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    // Inline fetch to avoid linter warning about calling setState in effect
    const loadDocs = async () => {
      const res = await fetch(`${API_BASE}/documents/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      // If unauthorized, clear token and redirect to login
      if (res.status === 401) {
        chatLogger.warn("Token expired or invalid, redirecting to login");
        localStorage.removeItem("token");
        window.location.href = "/login";
        return;
      }

      const data = await res.json();
      chatLogger.info("Documents loaded on mount", { count: data.documents?.length || 0 });
      setDocs(data.documents ?? []);
    };
    loadDocs();
  }, []);

  // Auto scroll when messages change
  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function upsertAssistantChunk(chunk: string) {
    setMessages((prev) => {
      const copy = [...prev];
      const last = copy[copy.length - 1];
      if (last && last.role === "assistant") {
        // APPEND chunk to existing content, don't overwrite
        last.content += chunk;
      } else {
        copy.push({ role: "assistant", content: chunk });
      }
      return copy;
    });
  }

  async function handleSend(userMessage: string) {
    const token = getToken();
    if (!userMessage.trim() || !token) return;

    chatLogger.info("Sending chat message", {
      messageLength: userMessage.length,
      selectedDocIds: selectedDocIds.length > 0 ? selectedDocIds : "all"
    });

    // Show user message instantly
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);

    setIsStreaming(true);

    // Create a conversation if one doesn't exist yet
    let currentConversationId = conversationId;
    if (!currentConversationId) {
      try {
        const convRes = await fetch(`${API_BASE}/chat/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          body: JSON.stringify({ title: userMessage.slice(0, 50) + (userMessage.length > 50 ? "..." : "") }),
        });
        if (!convRes.ok) {
          const err = await convRes.json().catch(() => ({ detail: "Failed to create conversation" }));
          chatLogger.error("Failed to create conversation", { error: err.detail });
          setMessages(prev => [...prev, { role: "assistant", content: `Error: ${err.detail}` }]);
          setIsStreaming(false);
          return;
        }
        const convData = await convRes.json();
        currentConversationId = convData.id;
        setConversationId(convData.id);
        chatLogger.info("Created new conversation", { conversationId: convData.id });
      } catch (e) {
        chatLogger.error("Failed to create conversation", { error: String(e) });
        setMessages(prev => [...prev, { role: "assistant", content: "Error: Failed to create conversation" }]);
        setIsStreaming(false);
        return;
      }
    }

    // Streaming Response
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({
        message: userMessage,
        conversation_id: currentConversationId,
        document_ids: selectedDocIds.length ? selectedDocIds : undefined,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Server error" }));
      chatLogger.error("Chat request failed", { status: response.status, error: err.detail });
      setMessages(prev => [...prev, { role: "assistant", content: `Error: ${err.detail || "unknown error"}` }]);
      setIsStreaming(false);
      return;
    }

    chatLogger.debug("Stream connection established");

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    // Track full answer for logging
    let fullAnswer = "";
    let buffer = "";
    let tokenCount = 0;

    let finalSources: { title: string; chunk_id: number }[] = [];

    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n")
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          // Parse SSE format - lines starting with "data: "
          if (!line.startsWith("data: ")) continue;

          const jsonStr = line.slice(6); // Remove "data: " prefix
          const event = JSON.parse(jsonStr);

          if (event.type === "token") {
            tokenCount++;
            const content = event.content;

            // Client-side duplicate detection - skip if this exact content was recently added
            // Check if this chunk would create visible repetition
            if (content && content.length > 10 && fullAnswer.length > 100) {
              const lastPart = fullAnswer.slice(-150).toLowerCase();
              const newPart = content.toLowerCase();
              if (lastPart.includes(newPart) && newPart.trim().length > 5) {
                chatLogger.debug("Skipping duplicate token on frontend", { token: content.slice(0, 30) });
                continue;
              }
            }

            // Track token for answer logging
            fullAnswer += content;
            // AI engine sends content, not token
            upsertAssistantChunk(content);
          }
          else if (event.type === "sources") {
            // attach sources to the last assistant message
            finalSources = event.sources ?? [];
            chatLogger.debug("Sources received", { count: finalSources.length });
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last && last.role === "assistant") {
                last.sources = finalSources
              }
              return copy;
            });
          }
          else if (event.type === "end") {
            // Stream has ended
            chatLogger.debug("Stream ended event received");
          }
          else if (event.type === "error") {
            chatLogger.error("Stream error event", { message: event.message });
            setMessages((p) => [...p, { role: "assistant", content: `Error: ${event.message}` }]);
          }
        } catch (e) {
          chatLogger.error("Failed to parse stream event", { error: String(e), line });
          console.error("Failed to parse stream event:", e, "Raw line:", line);
        }
      }
    }

    // Log the complete answer received from backend for comparison
    chatLogger.logAnswer("FRONTEND_RECEIVED_ANSWER", fullAnswer, {
      query: userMessage,
      tokenCount,
      sourcesCount: finalSources.length,
      documentIds: selectedDocIds.length > 0 ? selectedDocIds : "all"
    });

    setIsStreaming(false);
  }

  function downloadTranscript() {
    const text = messages.map((m) => `${m.role.toUpperCase()}:\n${m.content}\n\n`).join("");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar for documents */}
      <aside className="w-64 border-r border-gray-800 p-4 flex flex-col gap-3 bg-gray-950">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold">Documents</h2>
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
            title="Upload new documents"
          >
            + Upload
          </button>
          {selectedDocIds.length > 0 && (
            <button
              onClick={handleDeleteSelected}
              className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded transition-colors"
              title="Delete selected documents"
            >
              🗑 Delete ({selectedDocIds.length})
            </button>
          )}
        </div>
        {docs.length === 0 ? (
          <p className="text-xs text-gray-400">No documents. Click &quot;Upload&quot; to add PDFs.</p>
        ) : (
          <div className="space-y-2 text-sm">
            {docs.map((doc) => (
              <label key={doc.id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="accent-blue-500"
                  checked={selectedDocIds.includes(doc.id)}
                  onChange={(e) => {
                    setSelectedDocIds((prev) =>
                      e.target.checked
                        ? [...prev, doc.id]
                        : prev.filter((id) => id !== doc.id)
                    );
                  }}
                />
                <span className="truncate">{doc.title}</span>
              </label>
            ))}
          </div>
        )}

        <p className="mt-auto text-[11px] text-gray-500">
          Only selected docs will be used in answers. If none selected, all docs
          are used.
        </p>
      </aside>

      {/* Main chat area */}
      <div className="flex flex-col flex-1">
        {/* Header */}
        <div className="border-b border-gray-800 p-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Chat</h1>
            <p className="text-sm text-gray-400">
              {selectedDocIds.length > 0
                ? `Using ${selectedDocIds.length} document${selectedDocIds.length !== 1 ? "s" : ""}`
                : "Using all documents"}
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={downloadTranscript}
              className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              Download
            </button>
          )}
        </div>

        {/* Messages */}
        <div
          ref={chatRef}
          className="flex-1 overflow-y-auto p-4 space-y-4"
        >
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>Start a conversation...</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatBubble key={i} role={msg.role} content={msg.content} sources={msg.sources} />
          ))}
          {isStreaming && (
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
              <span>AI is thinking...</span>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-800 p-4">
          <ChatInput onSend={handleSend} />
        </div>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadComplete={() => {
          // Refresh the documents list after upload
          const token = getToken();
          if (token) {
            fetch(`${API_BASE}/documents/`, {
              headers: { Authorization: `Bearer ${token}` },
            })
              .then((res) => res.json())
              .then((data) => setDocs(data.documents ?? []));
          }
        }}
      />
    </div>
  );
}
