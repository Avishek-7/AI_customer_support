"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export default function ChatHistoryPage() {
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/chat/history`, {
      headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
    })
      .then(res => res.json())
      .then(data => setHistory(data.history));
  }, []);

  return (
    <div className="p-6 text-white bg-gray-900 min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Chat History</h1>

      <div className="space-y-4">
        {history.map((item, i) => (
          <div key={i} className="p-4 border border-gray-700 rounded-lg bg-gray-800">
            <p className="font-semibold text-blue-400">You:</p>
            <p>{item.message}</p>

            <p className="mt-3 font-semibold text-green-400">AI Response:</p>
            <p>{item.response}</p>

            <p className="text-xs opacity-60 mt-2">
              {new Date(item.timestamp).toLocaleString()}
            </p>
          </div>

        ))}
      </div>
    </div>
  )
}
