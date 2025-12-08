"use client";

import { send } from "process";
import { useState } from "react";

export default function ChatInput({ onSend }: { onSend: (msg: string) => void }) {
    const [value, setValue] = useState("");

    const sendMessage = () => {
        if (!value.trim()) return;
        onSend(value);
        setValue("");
    };

    return (
        <div className="p-4 border-t border-gray-700 flex gap-2 bg-gray-800">
            <input
                type={value}
                onChange={e => setValue(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendMessage()}
                className="flex-1 bg-gray-900 border border-gray-700 px-3 py-2 rounded-md
                    focus:outline-none text-white"
                placeholder="Ask something..."
            />
            <button
                onClick={sendMessage}
                className="px-4 py-2 bg-blue-600 rounded-md hover:bg-blue-700"
            >
                Send
            </button>
        </div>
    );
}