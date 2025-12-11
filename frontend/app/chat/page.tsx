"use client";

import { useState, useRef, useEffect } from "react";
import ChatBubble from "./../../components/ChatBubble";
import ChatInput from "./../../components/ChatInput";

type Message = {
    role: "user" | "assistant";
    content: string;
    sources?: { title: string; chunk_id: number }[];
}

const updateAssistantToken = (prev: Message[], token: string): Message[] => {
    const updated = [...prev];
    const last = updated[updated.length - 1];

    if (!last || last.role !== "assistant") {
        updated.push({ role: "assistant", content: token, sources: [] });
        return updated;
    }

    last.content += token;
    return updated;
};

const updateAssistantSources = (
    prev: Message[],
    sources: { title?: string; chunk_id?: number }[]
): Message[] => {
    const updated = [...prev];
    const last = updated[updated.length - 1];
    if (!last || last.role !== "assistant") return updated;

    last.sources = (sources || []).map((src) => ({
        title: src.title ?? "Untitled",
        chunk_id: src.chunk_id ?? 0,
    }));
    return updated;
};

type DocumentItem = { id: number; title: string };

export default function ChatPage() {
    const [message, setMessage] = useState<Message[]>([]);
    const [docs, setDocs] = useState<DocumentItem[]>([]);
    const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
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
    }, [message]);

    const handleSend = async (message: string) => {
        if (!message.trim() || !token) return;

        // Show user message instantly
        setMessage(prev => [...prev, { role: "user", content: message }]);

        // Streaming Response
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
            body: JSON.stringify({
                message, 
                document_ids: selectedDocIds.length ? selectedDocIds : undefined,
            }),
        });

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        // let aiResponse = "";
        let buffer = "";

        while (true) {
            const { done, value } = await reader!.read();
            if (done) break;

            buffer += new TextDecoder().decode(value)

            const chunk = decoder.decode(value, { stream: true });
            const lines = buffer.split("\n")
            buffer = lines.pop() || "";
            // aiResponse += chunk;

            for (const line of lines) {
                if (!line.trim()) continue;

                const event = JSON.parse(line);
                if (event.type === "token") {
                    setMessage((prev) => updateAssistantToken(prev, event.content));
                }

                if (event.type === "final") {
                    setMessage((prev) => updateAssistantSources(prev, event.sources));
                } 

                if (event.type === "error") {
                    console.error("Error from stream:", event.message);
                }
            }

        }
    };

    return (
        <div className="flex h-screen bg-gray-900 text-white">
            {/* Sidebar for documents */}
            <aside className="w-64 border-r border-gray-800 p-4 flex flex-col gap-3 bg-gray-950">
            <h2 className="font-semibold mb-2">Documents</h2>
            {docs.length === 0 ? (
                <p className="text-xs text-gray-400">No documents. Upload on /documents</p>
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
                <div className="border-b border-gray-800 p-4">
                    <h1 className="text-2xl font-bold">Chat</h1>
                    <p className="text-sm text-gray-400">
                        {selectedDocIds.length > 0
                            ? `Using ${selectedDocIds.length} document${selectedDocIds.length !== 1 ? "s" : ""}`
                            : "Using all documents"}
                    </p>
                </div>

                {/* Messages */}
                <div
                    ref={chatRef}
                    className="flex-1 overflow-y-auto p-4 space-y-4"
                >
                    {message.length === 0 && (
                        <div className="flex items-center justify-center h-full text-gray-400">
                            <p>Start a conversation...</p>
                        </div>
                    )}
                    {message.map((msg, i) => (
                        <ChatBubble key={i} role={msg.role} content={msg.content} sources={msg.sources} />
                    ))}
                </div>

                {/* Input */}
                <div className="border-t border-gray-800 p-4">
                    <ChatInput onSend={handleSend} />
                </div>
            </div>
        </div>
    );
}