"use client";

import { useEffect, useRef, useState } from "react";
import Navigation from "@/components/Navigation";
import { docsLogger } from "@/lib/logger";
import { getAuthHeaders, getStoredToken } from "@/lib/auth";
import {
  updateDocument,
  searchDocuments,
  reindexDocument,
  getDocumentStatus,
} from "@/lib/api";

type Document = {
  id: number;
  title: string;
  content: string;
  owner_id: number;
  index_status?: string;
  chunk_count?: number;
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
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Document[]>([]);
  const [searching, setSearching] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [reindexing, setReindexing] = useState<number | null>(null);
  const pollingIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  const fetchDocs = async () => {
    const token = getStoredToken();
    if (!token) return;
    setLoading(true);
    docsLogger.info("Fetching documents");
    try {
      const res = await fetch(`${API_BASE}/documents/`, {
        headers: getAuthHeaders(token),
      });
      if (!res.ok) {
        const errorText = await res.text();
        docsLogger.error("Failed to fetch documents", {
          status: res.status,
          response: errorText,
        });
        throw new Error(`Failed to fetch documents (${res.status})`);
      }
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
    const token = getStoredToken();
    if (!token) {
      window.location.href = "/login";
      return;
    }
    fetchDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async () => {
    const token = getStoredToken();
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
          ...getAuthHeaders(token),
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
    const token = getStoredToken();
    if (!token) return;

    if (pollingIntervalRef.current) {
      clearTimeout(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    docsLogger.info("Starting index status polling", { docId });

    const poll = async () => {
      try {
        const status = await getDocumentStatus(docId, token);

        docsLogger.debug("Index status update", { docId, status: status.status, chunkCount: status.chunk_count });

        setIndexStatus(status.status);
        setChunkCount(status.chunk_count);

        if (status.status === "completed") {
          docsLogger.info("Document indexing completed", { docId, chunkCount: status.chunk_count });
          if (pollingIntervalRef.current) {
            clearTimeout(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setIndexStatus(null);
          setChunkCount(null);
          await fetchDocs();
          return;
        }

        if (status.status === "failed") {
          docsLogger.error("Document indexing failed", { docId });
          if (pollingIntervalRef.current) {
            clearTimeout(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setError("Document indexing failed");
          setIndexStatus(null);
          setChunkCount(null);
          return;
        }
      } catch (err) {
        docsLogger.error("Polling error", { docId, error: String(err) });
        console.error("Polling error:", err);
      }

      pollingIntervalRef.current = setTimeout(poll, 2000);
    };

    await poll();
  };

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearTimeout(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

  // Handle document search
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const token = getStoredToken();
    if (!token) return;

    setSearching(true);
    docsLogger.info("Searching documents", { query: searchQuery });

    try {
      const data = await searchDocuments(searchQuery, token);
      setSearchResults(data.documents ?? []);
      docsLogger.info("Search completed", { count: data.documents?.length || 0 });
    } catch (err) {
      docsLogger.error("Search failed", { error: String(err) });
      setError("Search failed");
    } finally {
      setSearching(false);
    }
  };

  // Handle edit document
  const handleEditStart = (doc: Document) => {
    setEditingId(doc.id);
    setEditTitle(doc.title);
    setEditContent(doc.content);
  };

  const handleEditSave = async (docId: number) => {
    const token = getToken();
    if (!token) return;

    docsLogger.info("Updating document", { docId, title: editTitle });

    try {
      const updated = await updateDocument(docId, token, {
        title: editTitle,
        content: editContent,
      });
      
      // Update in docs list
      setDocs((prev) =>
        prev.map((doc) =>
          doc.id === docId ? { ...doc, ...updated } : doc
        )
      );
      
      setEditingId(null);
      docsLogger.info("Document updated successfully", { docId });
    } catch (err) {
      docsLogger.error("Failed to update document", { error: String(err) });
      setError("Failed to update document");
    }
  };

  // Handle reindex
  const handleReindex = async (docId: number) => {
    const token = getToken();
    if (!token) return;

    if (!confirm("Re-index this document? This may take a moment.")) return;

    setReindexing(docId);
    docsLogger.info("Reindexing document", { docId });

    try {
      await reindexDocument(docId, token);
      docsLogger.info("Reindex completed", { docId });
      await fetchDocs();
    } catch (err) {
      docsLogger.error("Failed to reindex document", { error: String(err) });
      setError("Failed to reindex document");
    } finally {
      setReindexing(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <Navigation />
      <div className="flex-1 p-6 space-y-6">
        <h1 className="text-3xl font-bold">Documents</h1>

      {error && (
        <div className="bg-red-900 text-red-200 p-4 rounded-lg">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-4 text-sm underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Upload card */}
      <div className="bg-gray-800 p-6 rounded-lg space-y-4 max-w-2xl">
        <h2 className="font-semibold text-lg">Upload PDF Document</h2>
        <input
          className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
          placeholder="Document title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-sm text-gray-300"
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
        <button
          onClick={handleUpload}
          disabled={uploading || !file || !title.trim()}
          className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 font-semibold"
        >
          Upload
        </button>
      </div>

      {/* Search card */}
      <div className="bg-gray-800 p-6 rounded-lg space-y-4 max-w-2xl">
        <h2 className="font-semibold text-lg">Search Documents</h2>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            placeholder="Search document content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
          />
          <button
            type="submit"
            disabled={searching}
            className="px-4 py-2 rounded bg-green-600 hover:bg-green-700 disabled:opacity-50 font-semibold"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </form>
        {searchResults.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-sm text-gray-400">{searchResults.length} result(s) found</p>
            {searchResults.map((doc) => (
              <div key={doc.id} className="p-3 bg-gray-700 rounded text-sm">
                <p className="font-semibold">{doc.title}</p>
                <p className="text-gray-300 line-clamp-2">{doc.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Documents list */}
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="font-semibold text-lg mb-4">Your Documents</h2>
        {loading ? (
          <p>Loading…</p>
        ) : docs.length === 0 ? (
          <p className="text-sm text-gray-400">
            No documents yet. Upload a PDF to get started.
          </p>
        ) : (
          <div className="space-y-3">
            {docs.map((doc) => (
              <div key={doc.id} className="border border-gray-700 rounded-lg p-4 space-y-3">
                {editingId === doc.id ? (
                  // Edit mode
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white"
                      placeholder="Document title"
                    />
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white h-24"
                      placeholder="Document content"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditSave(doc.id)}
                        className="px-3 py-1 rounded bg-green-600 hover:bg-green-700 text-sm font-semibold"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1 rounded bg-gray-600 hover:bg-gray-500 text-sm font-semibold"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  // View mode
                  <div>
                    <p className="font-semibold text-lg">{doc.title}</p>
                    <p className="text-xs text-gray-400 mt-1">ID: {doc.id}</p>
                    {doc.index_status && (
                      <p className="text-xs text-blue-400 mt-1">
                        Status: {doc.index_status}
                        {doc.chunk_count != null ? ` (${doc.chunk_count} chunks)` : ""}
                      </p>
                    )}
                    <p className="text-sm text-gray-300 mt-2 line-clamp-2">{doc.content}</p>
                    
                    <div className="flex gap-2 mt-3 flex-wrap">
                      <button
                        onClick={() => handleEditStart(doc)}
                        className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-700 text-sm font-semibold"
                      >
                        ✎ Edit
                      </button>
                      <button
                        onClick={() => handleReindex(doc.id)}
                        disabled={reindexing === doc.id}
                        className="px-3 py-1 rounded bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-sm font-semibold"
                      >
                        {reindexing === doc.id ? "Reindexing..." : "↻ Reindex"}
                      </button>
                      <button
                        onClick={async () => {
                          const token = getToken();
                          if (token && confirm("Delete this document?")) {
                            try {
                              const res = await fetch(`${API_BASE}/documents/${doc.id}`, {
                                method: "DELETE",
                                headers: { Authorization: `Bearer ${token}` },
                              });
                              if (!res.ok) {
                                const responseText = await res.text();
                                console.error("Failed to delete document", {
                                  docId: doc.id,
                                  status: res.status,
                                  response: responseText,
                                });
                                setError(`Failed to delete document (${res.status})`);
                                return;
                              }
                              console.log("Document deleted", { docId: doc.id });
                              await fetchDocs();
                            } catch (err) {
                              setError("Failed to delete document");
                            }
                          }
                        }}
                        className="px-3 py-1 rounded bg-red-600 hover:bg-red-700 text-sm font-semibold"
                      >
                        🗑 Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
