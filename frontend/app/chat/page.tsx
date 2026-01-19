"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ChatBubble from "./../../components/ChatBubble";
import ChatInput from "./../../components/ChatInput";
import UploadModal from "./../../components/UploadModal";
import ConversationList from "./../../components/ConversationList";
import Navigation from "./../../components/Navigation";
import { chatLogger } from "@/lib/logger";
import {
  streamChatMessage,
  getAllConversations,
  createConversation,
  updateConversation,
  deleteConversation,
  getConversationMessages,
} from "@/lib/api";

type Source = { title?: string; document_id?: number; chunk_id?: number };

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

type DocumentItem = { id: number; title: string };

type Conversation = {
  id: number;
  title: string;
  created_at: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);

  const chatRef = useRef<HTMLDivElement>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  const getToken = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  };

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setLoadingConversations(true);
    try {
      const data = await getAllConversations(token);
      setConversations(data.conversations ?? []);
      chatLogger.info("Conversations loaded", { count: data.conversations?.length || 0 });
    } catch (err) {
      chatLogger.error("Failed to fetch conversations", { error: String(err) });
    } finally {
      setLoadingConversations(false);
    }
  }, []);

  // Fetch documents
  const fetchDocs = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    chatLogger.debug("Fetching documents");
    try {
      const res = await fetch(`${API_BASE}/documents/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        chatLogger.warn("Token expired, redirecting to login");
        localStorage.removeItem("token");
        window.location.href = "/login";
        return;
      }

      const data = await res.json();
      setDocs(data.documents ?? []);
      chatLogger.info("Documents loaded", { count: data.documents?.length || 0 });
    } catch (err) {
      chatLogger.error("Failed to fetch documents", { error: String(err) });
    }
  }, [API_BASE]);

  // Load conversation messages
  const loadConversation = useCallback(
    async (convId: number) => {
      const token = getToken();
      if (!token) return;
      try {
        const data = await getConversationMessages(convId, token);
        setMessages(data.history ?? []);
        setConversationId(convId);
        chatLogger.info("Conversation loaded", { conversationId: convId, messageCount: data.history?.length });
      } catch (err) {
        chatLogger.error("Failed to load conversation", { error: String(err) });
      }
    },
    []
  );

  // Create new conversation
  const handleCreateConversation = async () => {
    const token = getToken();
    if (!token) return;
    try {
      const data = await createConversation(token);
      setConversationId(data.id);
      setMessages([]);
      await fetchConversations();
      chatLogger.info("New conversation created", { conversationId: data.id });
    } catch (err) {
      chatLogger.error("Failed to create conversation", { error: String(err) });
    }
  };

  // Rename conversation
  const handleRenameConversation = async (convId: number, title: string) => {
    const token = getToken();
    if (!token) return;
    try {
      await updateConversation(convId, token, title);
      await fetchConversations();
      if (conversationId === convId) {
        // Update title in state if it's the current conversation
      }
      chatLogger.info("Conversation renamed", { conversationId: convId, title });
    } catch (err) {
      chatLogger.error("Failed to rename conversation", { error: String(err) });
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (convId: number) => {
    const token = getToken();
    if (!token) return;
    try {
      await deleteConversation(convId, token);
      if (conversationId === convId) {
        setConversationId(null);
        setMessages([]);
      }
      await fetchConversations();
      chatLogger.info("Conversation deleted", { conversationId: convId });
    } catch (err) {
      chatLogger.error("Failed to delete conversation", { error: String(err) });
    }
  };

  // Check authentication and load data on mount
  useEffect(() => {
    const token = getToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }

    fetchDocs();
    fetchConversations();
  }, [fetchDocs, fetchConversations]);

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
      selectedDocIds: selectedDocIds.length > 0 ? selectedDocIds : "all",
    });

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsStreaming(true);

    let currentConversationId = conversationId;
    if (!currentConversationId) {
      try {
        const data = await createConversation(
          token,
          userMessage.slice(0, 50) + (userMessage.length > 50 ? "..." : "")
        );
        currentConversationId = data.id;
        setConversationId(data.id);
        await fetchConversations();
        chatLogger.info("Created new conversation", { conversationId: data.id });
      } catch (e) {
        chatLogger.error("Failed to create conversation", { error: String(e) });
        setMessages((prev) => [...prev, { role: "assistant", content: "Error: Failed to create conversation" }]);
        setIsStreaming(false);
        return;
      }
    }

    try {
      let fullAnswer = "";
      let finalSources: Source[] = [];
      
      if (!currentConversationId) {
        setMessages((prev) => [...prev, { role: "assistant", content: "Error: No conversation selected" }]);
        setIsStreaming(false);
        return;
      }

      await streamChatMessage(userMessage, currentConversationId, token, (chunk) => {
        try {
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (!line.trim() || !line.startsWith("data: ")) continue;

            const jsonStr = line.slice(6);
            const event = JSON.parse(jsonStr);

            if (event.type === "token") {
              fullAnswer += event.content;
              upsertAssistantChunk(event.content);
            } else if (event.type === "sources") {
              finalSources = event.sources ?? [];
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (last && last.role === "assistant") {
                  last.sources = finalSources;
                }
                return copy;
              });
            }
          }
        } catch (e) {
          chatLogger.error("Failed to parse stream event", { error: String(e) });
        }
      });

      chatLogger.logAnswer("FRONTEND_RECEIVED_ANSWER", fullAnswer, {
        query: userMessage,
        sourcesCount: finalSources.length,
      });
    } catch (err) {
      chatLogger.error("Chat request failed", { error: String(err) });
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${String(err)}` }]);
    } finally {
      setIsStreaming(false);
    }
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
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <Navigation />
      <div className="flex flex-1 overflow-hidden">
        {/* Conversations Sidebar */}
        <div className="w-64 border-r border-gray-700 bg-gray-800 flex flex-col">
          <ConversationList
            conversations={conversations}
            activeId={conversationId}
            onSelect={loadConversation}
            onRename={handleRenameConversation}
            onDelete={handleDeleteConversation}
            onCreateNew={handleCreateConversation}
            loading={loadingConversations}
          />
        </div>

        {/* Documents Sidebar */}
        <aside className="w-64 border-r border-gray-800 p-4 flex flex-col gap-3 bg-gray-950">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-sm">Documents</h2>
            <button
              onClick={() => setShowUploadModal(true)}
              className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
            >
              + Upload
            </button>
          </div>
          {docs.length === 0 ? (
            <p className="text-xs text-gray-400">No documents uploaded yet.</p>
          ) : (
            <div className="space-y-2 text-sm overflow-y-auto flex-1">
              {docs.map((doc) => (
                <label key={doc.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-800 p-2 rounded">
                  <input
                    type="checkbox"
                    className="accent-blue-500"
                    checked={selectedDocIds.includes(doc.id)}
                    onChange={(e) => {
                      setSelectedDocIds((prev) =>
                        e.target.checked ? [...prev, doc.id] : prev.filter((id) => id !== doc.id)
                      );
                    }}
                  />
                  <span className="truncate text-xs">{doc.title}</span>
                </label>
              ))}
            </div>
          )}
          <p className="mt-auto text-[11px] text-gray-500">
            {selectedDocIds.length > 0 ? `Using ${selectedDocIds.length} doc(s)` : "Using all docs"}
          </p>
        </aside>

        {/* Main Chat Area */}
        <div className="flex flex-col flex-1">
          {/* Header */}
          <div className="border-b border-gray-800 p-4 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Chat</h1>
              <p className="text-sm text-gray-400">{conversationId ? `Conversation #${conversationId}` : "No conversation selected"}</p>
            </div>
            {messages.length > 0 && (
              <button onClick={downloadTranscript} className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg">
                Download
              </button>
            )}
          </div>

          {/* Messages */}
          <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {!conversationId ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <p className="text-lg mb-4">Create or select a conversation to start</p>
                  <button
                    onClick={handleCreateConversation}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-semibold"
                  >
                    + New Conversation
                  </button>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <p>Start a conversation...</p>
              </div>
            ) : (
              <>
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
              </>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-gray-800 p-4">{conversationId && <ChatInput onSend={handleSend} />}</div>
        </div>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploadComplete={() => fetchDocs()}
      />
    </div>
  );
}
