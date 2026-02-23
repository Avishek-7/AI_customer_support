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
        aria-label="Chat input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            sendMessage();
          }
        }}
        rows={1}
        className="flex-1 resize-none bg-gray-900 border border-gray-700 px-2 md:px-3 py-2 rounded-md text-sm md:text-base text-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
        placeholder="Ask a question (Ctrl/Cmd+Enter to send)"
      />
      <button 
        onClick={sendMessage} 
        className="bg-blue-600 hover:bg-blue-700 px-3 md:px-4 py-2 rounded-md text-sm md:text-base font-medium transition-colors flex-shrink-0"
      >
        Send
      </button>
    </div>
  )
}
