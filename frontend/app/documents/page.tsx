"use client";

import { useEffect, useState } from "react";
import { docsLogger } from "@/lib/logger";

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
    const [indexStatus, setIndexStatus] = useState<string | null>(null);
    const [chunkCount, setChunkCount] = useState<number | null>(null);

    const API_BASE = "http://localhost:8000";

    // Get token - only available on client side
    const getToken = () => {
        if (typeof window === "undefined") return null;
        return localStorage.getItem("token");
    };

    const fetchDocs = async () => {
        const token = getToken();
        if (!token) return;
        setLoading(true);
        docsLogger.info("Fetching documents");
        try {
            const res = await fetch(`${API_BASE}/documents/`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            docsLogger.info("Documents fetched", { count: data.documents?.length || 0 });
            setDocs(data.documents ?? []);
        } catch (err) {
            docsLogger.error("Failed to fetch documents", { error: String(err) });
            console.error(err);
            setError("Failed to fetch documents.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const token = getToken();
        if (!token) {
            window.location.href = "/login";
            return;
        }
        fetchDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleUpload = async () => {
        const token = getToken();
        if (!file || !title.trim() || !token) return;

        setUploading(true);
        setError(null);
        docsLogger.info("Starting document upload", { title, fileName: file.name, fileSize: file.size });

        const formData = new FormData();
        formData.append("title", title);
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE}/documents/upload`, {
                method: "POST",
                headers: { 
                    "Authorization": `Bearer ${token}` 
                },
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                docsLogger.error("Upload failed", { status: res.status, error: err });
                console.error("Upload error details:", err);
                // Extract error message from Pydantic validation errors
                let errorMsg = "Upload failed";
                if (err.detail) {
                    if (Array.isArray(err.detail)) {
                        errorMsg = err.detail.map((e: { loc?: string[]; msg: string }) => `${e.loc?.[1] || 'field'}: ${e.msg}`).join(", ");
                    } else if (typeof err.detail === 'string') {
                        errorMsg = err.detail;
                    }
                }
                throw new Error(errorMsg);
            }

            const data = await res.json();
            const docId = data.id;
            docsLogger.info("Document uploaded successfully", { docId, title });

            setTitle("");
            setFile(null);
            await fetchDocs();

            // Start polling for index status
            if (docId) {
                pollIndexStatus(docId);
            }
        } catch (err: unknown) {
            console.error(err);
            const errorMessage = err instanceof Error ? err.message : "Upload failed.";
            setError(errorMessage);
        } finally {
            setUploading(false);
        }
    };

    const pollIndexStatus = async (docId: number) => {
        const token = getToken();
        if (!token) return;
        
        docsLogger.info("Starting index status polling", { docId });

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/documents/status/${docId}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                const status = await res.json();
                
                docsLogger.debug("Index status update", { docId, status: status.status, chunkCount: status.chunk_count });

                setIndexStatus(status.status);
                setChunkCount(status.chunk_count);

                if (status.status === "completed") {
                    docsLogger.info("Document indexing completed", { docId, chunkCount: status.chunk_count });
                    clearInterval(interval);
                    setIndexStatus(null);
                    setChunkCount(null);
                    await fetchDocs();
                }

                if (status.status === "failed") {
                    docsLogger.error("Document indexing failed", { docId });
                    clearInterval(interval);
                    setError("Document indexing failed");
                    setIndexStatus(null);
                    setChunkCount(null);
                }
            } catch (err) {
                docsLogger.error("Polling error", { docId, error: String(err) });
                console.error("Polling error:", err);
            }
        }, 2000); // Poll every 2 seconds
    }

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
            {indexStatus && (
            <p className="text-sm text-blue-400">
                Index status: {indexStatus}
                {chunkCount !== null && ` (${chunkCount} chunks)`}
            </p>
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