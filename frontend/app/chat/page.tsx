"use client";

import { useState, useRef, useEffect } from "react";
import ChatBubble from "./../../components/ChatBubble";
import ChatInput from "./../../components/ChatInput";

export default function ChatPage() {
    const [message, setMessage] = useState<{ role: "user" | "assistant", content: string }[]>([]);
    const chatRef = useRef<HTMLDivElement>(null);

    // Auto scroll
    useEffect(() => {
        chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth"});
    }, [message]);

    const handleSend = async (message: string) => {
        if (!message.trim()) return;

        // Show user message instantly
        setMessage(prev => [...prev, { role: "user", content: message }]);

        // Streaming Response
        const response = await fetch("http://localhost:8000/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("token")}`},
            body: JSON.stringify({ message }),
        });

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let aiResponse = "";

        while (true) {
            const { done, value } = await reader!.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });

            // Live streaming token-by-token rendering
            setMessage(prev => {
                const updated = [...prev];
                if (updated[updated.length - 1]?.role === "assistant") {
                    updated[updated.length - 1].content = aiResponse;
                } else {
                    updated.push({ role: "assistant", content: aiResponse });
                }
                return updated;
            });
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-900 text-white">
            <div className="p-4 text-2xl font-bold border-b border-gray-700">
                AI Support Chat
            </div>

            <div ref={chatRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-3">
                {message.map((msg, i) => (
                    <ChatBubble key={i} role={msg.role} content={msg.content} />
                ))}
            </div>

            <ChatInput onSend={handleSend} />
        </div>
    );
}