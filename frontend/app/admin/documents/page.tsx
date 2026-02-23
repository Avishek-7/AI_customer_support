"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAdminDocuments } from "@/lib/api";

export default function AdminDocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getToken = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  };

  useEffect(() => {
    const loadDocuments = async () => {
      const token = getToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        setError(null);
        const data = await getAdminDocuments(token);
        setDocuments(data.documents || []);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to load documents";
        setError(message);
        setDocuments([]);
        console.error("Failed to load documents:", err);
      } finally {
        setLoading(false);
      }
    };

    loadDocuments();
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/admin" className="text-blue-400 hover:text-blue-300 text-sm mb-4 inline-block">
          ← Back to Admin
        </Link>
        <h1 className="text-4xl font-bold mb-8">All Documents</h1>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            {error && <p className="text-red-400 px-4 pt-4">{error}</p>}
            <div className="p-4 bg-gray-700 flex items-center justify-between">
              <p className="font-semibold">Total: {documents.length} documents</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Title</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Owner</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Status</th>
                    <th className="px-6 py-3 text-center text-sm font-semibold">Chunks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {documents.map((doc, idx) => (
                    <tr key={idx} className="hover:bg-gray-700 transition">
                      <td className="px-6 py-4 font-medium">{String(doc.title)}</td>
                      <td className="px-6 py-4 text-sm text-gray-300">User #{String(doc.owner_id)}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          doc.index_status === "completed"
                            ? "bg-green-600 text-green-200"
                            : doc.index_status === "pending"
                            ? "bg-yellow-600 text-yellow-200"
                            : doc.index_status === "processing"
                            ? "bg-blue-600 text-blue-200"
                            : "bg-red-600 text-red-200"
                        }`}>
                          {String(doc.index_status) || "unknown"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">{String(doc.chunk_count)}</td>
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
