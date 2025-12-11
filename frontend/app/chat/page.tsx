"use client";

import { useState, useRef, useEffect } from "react";
import ChatBubble from "./../../components/ChatBubble";
import ChatInput from "./../../components/ChatInput";

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

  const chatRef = useRef<HTMLDivElement>(null);
  const API_BASE = "http://localhost:8000";
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  // Auto scroll
  // Check authentication once on mount
  useEffect(() => {
    if (!token) {
      window.location.href = "/login";
      return;
    }

    const fetchDocs = async () => {
      const res = await fetch(`${API_BASE}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setDocs(data.documents ?? []);
    };
    fetchDocs();
  }, [token]);

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
    if (!userMessage.trim() || !token) return;

    // Show user message instantly
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);

    setIsStreaming(true);

    // Streaming Response
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({
        message: userMessage,
        document_ids: selectedDocIds.length ? selectedDocIds : undefined,
      }),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Server error" }));
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${err.detail || "unknown error"}` }]);
        setIsStreaming(false);
        return;
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    // let aiResponse = "";
    let buffer = "";

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
                // AI engine sends content, not token
                upsertAssistantChunk(event.content);
            }       
            else if (event.type === "sources") {
                // attach sources to the last assistant message
                finalSources = event.sources ?? [];
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
                console.log("Stream ended");
            }
            else if (event.type === "error") {
                setMessages((p) => [...p, { role: "assistant", content: `Error: ${event.message}` }]);
            }
        } catch (e) {
          console.error("Failed to parse stream event:", e, "Raw line:", line);
        }
      }
    }
  
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
            onClick={() => window.location.href = "/documents"}
            className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
            title="Upload new documents"
          >
            + Upload
          </button>
        </div>
        {docs.length === 0 ? (
          <p className="text-xs text-gray-400">No documents. Click "Upload" to add PDFs.</p>
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
    </div>
  );
}
