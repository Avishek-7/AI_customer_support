"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAdminChats } from "@/lib/api";

export default function AdminChatsPage() {
  const router = useRouter();
  const [chats, setChats] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatTimestamp = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  };

  const getToken = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  };

  useEffect(() => {
    const loadChats = async () => {
      const token = getToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        setError(null);
        const data = await getAdminChats(token);
        setChats(data.recent_chats || []);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to load chats";
        setError(message);
        console.error("Failed to load chats:", err);
      } finally {
        setLoading(false);
      }
    };

    loadChats();
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/admin" className="text-blue-400 hover:text-blue-300 text-sm mb-4 inline-block">
          ← Back to Admin
        </Link>
        <h1 className="text-4xl font-bold mb-8">Recent Chats</h1>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            {error && <p className="text-red-400 mb-4 px-4 pt-4">{error}</p>}
            <div className="p-4 bg-gray-700 flex items-center justify-between">
              <p className="font-semibold">Recent: {chats.length} chats</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left font-semibold">User</th>
                    <th className="px-6 py-3 text-left font-semibold">Message</th>
                    <th className="px-6 py-3 text-left font-semibold">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {chats.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-6 py-8 text-center text-gray-400">
                        No chats
                      </td>
                    </tr>
                  ) : chats.map((chat) => (
                    <tr key={String(chat.id ?? `${String(chat.user_id)}-${String(chat.timestamp)}`)} className="hover:bg-gray-700 transition">
                      <td className="px-6 py-4 font-medium">User #{String(chat.user_id)}</td>
                      <td className="px-6 py-4 text-gray-300 max-w-md truncate">{String(chat.message)}</td>
                      <td className="px-6 py-4 text-gray-400">
                        {formatTimestamp(String(chat.timestamp))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
