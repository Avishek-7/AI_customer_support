"use client";

import { useState } from "react";

export default function ChatInput({ onSend }: { onSend: (msg: string) => void }) {
    const [value, setValue] = useState("");

    const sendMessage = () => {
        if (!value.trim()) return;
        onSend(value);
        setValue("");
    };

    return (
        <div className="flex gap-2">
            <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                        e.preventDefault();
                        sendMessage();
                    }
                }}
                rows={1}
                className="flex-1 resize-none bg-gray-900 border border-gray-700 px-3 py-2 rounded-md text-white focus:outline-none"
                placeholder="Ask a question (Ctrl/Cmt+Enter to send)"
            />
            <button onClick={sendMessage} className="bg-blue-600 px-4 py-2 rounded-md">Send</button>
        </div>
    )
}