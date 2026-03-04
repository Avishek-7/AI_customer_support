"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAdminConversationDebug } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

export default function AdminDebugPage() {
  const router = useRouter();
  const [conversationId, setConversationId] = useState("");
  const [debugData, setDebugData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!conversationId.trim()) {
      setError("Please enter a conversation ID");
      return;
    }

    const token = getStoredToken();
    if (!token) {
      router.push("/login");
      return;
    }

    setLoading(true);
    setError(null);
    setDebugData(null);

    try {
      const parsedId = Number.parseInt(conversationId, 10);
      if (!Number.isInteger(parsedId) || Number.isNaN(parsedId) || parsedId <= 0) {
        setError("Please enter a valid conversation ID");
        return;
      }
      const data = await getAdminConversationDebug(parsedId, token) as Record<string, unknown>;
      setDebugData(data);
    } catch (err) {
      setError("Failed to load conversation: " + String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/admin" className="text-blue-400 hover:text-blue-300 text-sm mb-4 inline-block">
          ← Back to Admin
        </Link>
        <h1 className="text-4xl font-bold mb-8">Conversation Debugger</h1>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="bg-gray-800 p-6 rounded-lg mb-8">
          <label htmlFor="conversation-id" className="block text-sm font-semibold mb-2">Conversation ID</label>
          <div className="flex gap-2">
            <input
              id="conversation-id"
              type="number"
              value={conversationId}
              onChange={(e) => setConversationId(e.target.value)}
              placeholder="Enter conversation ID"
              className="flex-1 px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 font-semibold"
            >
              {loading ? "Loading..." : "Debug"}
            </button>
          </div>
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        </form>

        {/* Debug Output */}
        {debugData ? (
          <div className="space-y-8">
            <div className="bg-gray-800 p-6 rounded-lg">
              <h2 className="text-2xl font-bold mb-4">Conversation Info</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-gray-400 text-sm">ID</p>
                  <p className="text-lg font-semibold">{String(debugData.conversation_id)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">User</p>
                  <p className="text-lg font-semibold">#{String(debugData.user_id)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Title</p>
                  <p className="text-lg font-semibold">{String(debugData.title)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Messages</p>
                  <p className="text-lg font-semibold">{String(debugData.message_count)}</p>
                </div>
              </div>
            </div>

            {!!((debugData as Record<string, unknown>)?.debug_info) ? (
              <div className="bg-gray-800 p-6 rounded-lg">
                <h2 className="text-2xl font-bold mb-4">RAG Pipeline Debug</h2>
                <div className="space-y-4">
                  <div>
                    <p className="text-gray-400 text-sm">Last Query</p>
                    <p className="text-white break-words">{String((debugData.debug_info as Record<string, unknown>)?.last_query || '')}</p>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="bg-gray-700 p-4 rounded">
                      <p className="text-gray-400 text-sm">Chunks Retrieved</p>
                      <p className="text-2xl font-bold text-blue-400">
                        {String((debugData.debug_info as Record<string, unknown>)?.total_chunks_retrieved || 0)}
                      </p>
                    </div>
                    <div className="bg-gray-700 p-4 rounded">
                      <p className="text-gray-400 text-sm">Confidence</p>
                      <p className="text-2xl font-bold text-green-400">
                        {((((debugData.debug_info as Record<string, unknown>)?.confidence_score as number) ?? 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div className="bg-gray-700 p-4 rounded">
                      <p className="text-gray-400 text-sm">Hallucination</p>
                      <p className="text-2xl font-bold text-orange-400">
                        {((((debugData.debug_info as Record<string, unknown>)?.hallucination_score as number) ?? 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div className="bg-gray-700 p-4 rounded">
                      <p className="text-gray-400 text-sm">Alignment</p>
                      <p className="text-2xl font-bold text-purple-400">
                        {((((debugData.debug_info as Record<string, unknown>)?.alignment_score as number) ?? 0) * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div className="bg-gray-700 p-4 rounded">
                      <p className="text-gray-400 text-sm">Prompt Length (words)</p>
                      <p className="text-lg font-bold">{String((debugData.debug_info as Record<string, unknown>)?.prompt_length_words || 0)}</p>
                    </div>
                    <div className="bg-gray-700 p-4 rounded">
                      <p className="text-gray-400 text-sm">Prompt Length (chars)</p>
                      <p className="text-lg font-bold">{String((debugData.debug_info as Record<string, unknown>)?.prompt_length_chars || 0)}</p>
                    </div>
                  </div>

                  {Array.isArray((debugData.debug_info as Record<string, unknown>)?.retrieved_chunks) && ((debugData.debug_info as Record<string, unknown>)?.retrieved_chunks as Array<unknown>).length > 0 && (
                    <div>
                      <p className="text-gray-400 text-sm mb-2">Retrieved Chunks</p>
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {((debugData.debug_info as Record<string, unknown>)?.retrieved_chunks as Array<Record<string, unknown>>).map((chunk: Record<string, unknown>, idx: number) => (
                          <div key={idx} className="bg-gray-700 p-3 rounded text-sm">
                            <p className="text-gray-400">Chunk {idx + 1} (Score: {(chunk.score as number | undefined)?.toFixed(3) || 'N/A'})</p>
                            <p className="text-white mt-1 line-clamp-2">{String(chunk.text)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
