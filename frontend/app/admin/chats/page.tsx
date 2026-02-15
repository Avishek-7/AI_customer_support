"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAdminChats } from "@/lib/api";

export default function AdminChatsPage() {
  const router = useRouter();
  const [chats, setChats] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);

  const formatTimestamp = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toISOString().replace("T", " ").slice(0, 19);
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
        const data = await getAdminChats(token);
        setChats(data.recent_chats || []);
      } catch (err) {
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
                  {chats.map((chat, idx) => (
                    <tr key={idx} className="hover:bg-gray-700 transition">
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
