"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export default function ChatHistoryPage() {
  const [history, setHistory] = useState<any[]>([]);

  const formatTimestamp = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString();
  };

  useEffect(() => {
    const run = async () => {
      if (!API_BASE) {
        console.error("NEXT_PUBLIC_API_URL is not configured");
        setHistory([]);
        return;
      }

      const token = localStorage.getItem("token");
      if (!token) {
        console.error("No auth token found");
        setHistory([]);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/chat/history`, {
          headers: { "Authorization": `Bearer ${token}` }
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`Failed to load chat history (${res.status}): ${errorText}`);
        }

        const data = await res.json();
        setHistory(Array.isArray(data?.history) ? data.history : []);
      } catch (error) {
        console.error("Failed to fetch chat history:", error);
        setHistory([]);
      }
    };

    run();
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
              {formatTimestamp(item.timestamp)}
            </p>
          </div>

        ))}
      </div>
    </div>
  )
}
