"use client";

import { use, useEffect, useState } from "react";

type Document = {
    id: number;
    title: string;
    content: string;
    owner_id: number;
};

export default function DocumentsPage() {
    const [docs, setDocs] = useState<Document[]>([]);
    const [title, setTitle] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const API_BASE = "http://localhost:8000";

    const token = 
        typeof window !== "undefined" ? localStorage.getItem("token") : null;

    const fetchDocs = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/documents`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            setDocs(data.documents ?? []);
        } catch (err) {
            console.error(err);
            setError("Failed to fetch documents.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocs();
    }, [token]);

    const handleUpload = async () => {
        if (!file || !title.trim() || !token) return;

        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append("title", title);
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE}/documents/upload`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.message || "Upload failed");
            }

            setTitle("");
            setFile(null);
            await fetchDocs();
        } catch (err: any) {
            console.error(err);
            setError(err.message || "Upload failed.");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6 space-y-6">
        <h1 className="text-2xl font-bold mb-2">Documents</h1>

        {/* Upload card */}
        <div className="bg-gray-800 p-4 rounded-lg space-y-3 max-w-xl">
            <h2 className="font-semibold text-lg">Upload PDF</h2>
            <input
            className="w-full px-3 py-2 rounded bg-gray-900 border border-gray-700"
            placeholder="Document title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            />
            <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="text-sm"
            />
            {uploading && (
            <p className="text-sm text-yellow-400">Uploading & indexing…</p>
            )}
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
            onClick={handleUpload}
            disabled={uploading || !file || !title.trim()}
            className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
            Upload
            </button>
        </div>

        {/* Documents list */}
        <div className="bg-gray-800 p-4 rounded-lg">
            <h2 className="font-semibold text-lg mb-3">Your Documents</h2>
            {loading ? (
            <p>Loading…</p>
            ) : docs.length === 0 ? (
            <p className="text-sm text-gray-400">
                No documents yet. Upload a PDF to get started.
            </p>
            ) : (
            <ul className="space-y-2">
                {docs.map((doc) => (
                <li
                    key={doc.id}
                    className="flex items-center justify-between border border-gray-700 rounded px-3 py-2"
                >
                    <div>
                    <p className="font-medium">{doc.title}</p>
                    <p className="text-xs text-gray-400">ID: {doc.id}</p>
                    </div>
                </li>
                ))}
            </ul>
            )}
        </div>
        </div>
    );
}