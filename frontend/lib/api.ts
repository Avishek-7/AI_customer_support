/**
 * Comprehensive API client for all backend endpoints
 */

import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_URL is required for frontend API client");
}

type RequestOptions = {
    method?: string;
    token?: string;
    body?: unknown;
    headers?: Record<string, string>;
    throwOnError?: boolean;
    allowNoContent?: boolean;
};

async function parseResponseBody(response: Response): Promise<unknown> {
    if (response.status === 204) {
        return null;
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return response.json().catch(() => ({}));
    }

    const text = await response.text().catch(() => "");
    return text || null;
}

function buildRequestHeaders(token?: string, extraHeaders?: Record<string, string>, hasBody?: boolean): Record<string, string> {
    const authHeaders = getAuthHeaders(token);
    const jsonHeaders: Record<string, string> = {};
    if (hasBody) {
        jsonHeaders["Content-Type"] = "application/json";
    }

    return {
        ...jsonHeaders,
        ...authHeaders,
        ...(extraHeaders || {}),
    };
}

async function requestJson<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", token, body, headers, throwOnError = false, allowNoContent = false } = options;
    const response = await fetch(`${API_BASE}${path}`, {
        method,
        headers: buildRequestHeaders(token, headers, body !== undefined),
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    const payload = await parseResponseBody(response);

    if (!response.ok && throwOnError) {
        const detail =
            typeof payload === "string"
                ? payload
                : (payload as { detail?: string } | null)?.detail || response.statusText;
        throw new Error(`Request failed (${response.status}): ${detail}`);
    }

    if (response.status === 204 && allowNoContent) {
        return null as T;
    }

    return payload as T;
}

// ============================================================================
// AUTHENTICATION APIs
// ============================================================================

export async function forgotPassword(email: string) {
    return requestJson("/auth/forgot-password", { method: "POST", body: { email } });
}

export async function resetPassword(token: string, newPassword: string) {
    return requestJson("/auth/reset-password", {
        method: "POST",
        body: { token, new_password: newPassword },
    });
}

export async function verifyResetToken(token: string) {
    return requestJson(`/auth/reset-password/${token}`);
}

// ============================================================================
// USER APIs
// ============================================================================

export async function getCurrentUser(token: string) {
    return requestJson("/users/me", { token });
}

export async function updateUser(userId: number, token: string, data: {
    name?: string;
    email?: string;
    password?: string;
    role?: string;
}) {
    return requestJson(`/users/${userId}`, { method: "PUT", token, body: data });
}

export async function getAllUsers(token: string) {
    return requestJson("/users/", { token });
}

export async function getUser(userId: number, token: string) {
    return requestJson(`/users/${userId}`, { token });
}

export async function createUser(token: string, data: {
    email: string;
    password: string;
    name?: string;
    role?: string;
}) {
    return requestJson("/users/", { method: "POST", token, body: data });
}

export async function deleteUser(userId: number, token: string) {
    return requestJson(`/users/${userId}`, {
        method: "DELETE",
        token,
        throwOnError: true,
        allowNoContent: true,
    });
}

// ============================================================================
// CONVERSATION APIs
// ============================================================================

export async function createConversation(token: string, title?: string) {
    return requestJson("/chat/conversations", {
        method: "POST",
        token,
        body: { title: title || "New Conversation" },
    });
}

export async function getAllConversations(token: string) {
    return requestJson("/chat/conversations", { token, throwOnError: true });
}

export async function getConversation(conversationId: number, token: string) {
    return requestJson(`/chat/conversations/${conversationId}`, { token });
}

export async function updateConversation(conversationId: number, token: string, title: string) {
    return requestJson(`/chat/conversations/${conversationId}`, {
        method: "PATCH",
        token,
        body: { title },
    });
}

export async function deleteConversation(conversationId: number, token: string) {
    return requestJson(`/chat/conversations/${conversationId}`, {
        method: "DELETE",
        token,
        allowNoContent: true,
    });
}

export async function getConversationMessages(conversationId: number, token: string) {
    return requestJson(`/chat/conversations/${conversationId}/messages`, {
        token,
        throwOnError: true,
    });
}

// ============================================================================
// CHAT APIs
// ============================================================================

export async function sendChatMessage(
    message: string,
    conversationId: number,
    token: string,
    data?: {
        system_prompt?: string;
        document_ids?: number[];
    }
) {
    return requestJson("/chat/chat", {
        method: "POST",
        token,
        body: {
            message,
            conversation_id: conversationId,
            ...(data?.system_prompt && { system_prompt: data.system_prompt }),
            ...(data?.document_ids && { document_ids: data.document_ids }),
        },
    });
}

export async function streamChatMessage(
    message: string,
    conversationId: number,
    token: string,
    onChunk: (chunk: string) => void,
    data?: {
        system_prompt?: string;
        document_ids?: number[];
    }
) {
    const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: buildRequestHeaders(token, undefined, true),
        body: JSON.stringify({
            message,
            conversation_id: conversationId,
            ...(data?.system_prompt && { system_prompt: data.system_prompt }),
            ...(data?.document_ids && { document_ids: data.document_ids }),
        }),
    });

    if (!response.ok) {
        let errorBody = "";
        try {
            errorBody = await response.text();
        } catch {
            errorBody = "";
        }
        throw new Error(`Stream chat request failed (${response.status}): ${errorBody || response.statusText}`);
    }

    if (!response.body) {
        throw new Error("Stream chat response body is empty");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) {
                onChunk(decoder.decode(value, { stream: true }));
            }
        }

        const remaining = decoder.decode();
        if (remaining) {
            onChunk(remaining);
        }
    } finally {
        await reader.cancel().catch(() => {});
    }
}

// ============================================================================
// DOCUMENT APIs
// ============================================================================

export async function updateDocument(
    docId: number,
    token: string,
    data: { title?: string; content?: string }
) {
    return requestJson(`/documents/${docId}`, { method: "PUT", token, body: data });
}

export async function searchDocuments(query: string, token: string) {
    return requestJson("/documents/search", { method: "POST", token, body: { query } });
}

export async function reindexDocument(docId: number, token: string) {
    return requestJson(`/documents/${docId}/reindex`, { method: "POST", token });
}

export async function getDocumentStatus(docId: number, token: string) {
    return requestJson(`/documents/status/${docId}`, { token });
}

// ============================================================================
// ADMIN APIs
// ============================================================================

export async function getAdminUsers(token: string) {
    return requestJson("/admin/users", { token });
}

export async function getAdminUsageStats(token: string) {
    return requestJson("/admin/usage-stats", { token });
}

export async function getAdminSystemStats(token: string) {
    return requestJson("/admin/system-stats", { token });
}

export async function getAdminUserUsage(userId: number, token: string) {
    return requestJson(`/admin/users/${userId}/usage`, { token });
}

export async function getAdminDocuments(token: string) {
    return requestJson("/admin/documents", { token });
}

export async function getAdminChats(token: string) {
    return requestJson("/admin/chats", { token });
}

export async function getAdminStats(token: string) {
    return requestJson("/admin/stats", { token });
}

export async function getAdminConversationDebug(conversationId: number, token: string) {
    return requestJson(`/admin/debug/conversations/${conversationId}`, { token });
}

// ============================================================================
// VECTOR APIs
// ============================================================================

export async function getVectorMetadata(docId: number) {
    return requestJson(`/vectors/document/${docId}`);
}

export async function getVectorStats() {
    return requestJson("/vectors/stats");
}
