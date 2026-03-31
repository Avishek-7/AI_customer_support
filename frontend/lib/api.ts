/**
 * Comprehensive API client for all backend endpoints
 */

import { getAuthHeaders } from "./auth";
import { getApiBase } from "./runtimeEnv";

function getApiBaseUrl(): string {
    const base = getApiBase();
    if (!base) {
        throw new Error("NEXT_PUBLIC_API_URL is required for frontend API client");
    }
    return base;
}

type RequestOptions = {
    method?: string;
    token?: string;
    body?: unknown;
    headers?: Record<string, string>;
    throwOnError?: boolean;
    allowNoContent?: boolean;
};

type ApiSource = {
    title?: string;
    document_id?: number;
    chunk_id?: number;
};

type ApiMessage = {
    role: "user" | "assistant";
    content: string;
    sources?: ApiSource[];
};

type ApiConversation = {
    id: number;
    title: string;
    created_at: string;
    updated_at?: string;
};

type GetAllConversationsResponse = {
    conversations?: ApiConversation[];
};

type ConversationMessagesResponse = {
    history?: ApiMessage[];
};

type ApiDocument = {
    id: number;
    title: string;
    content: string;
    owner_id: number;
    index_status?: string;
    chunk_count?: number;
};

type SearchDocumentsResponse = {
    documents?: ApiDocument[];
};

type DocumentStatusResponse = {
    status: string;
    chunk_count: number;
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
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
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
    return requestJson<{ message?: string; detail?: string }>("/auth/forgot-password", { method: "POST", body: { email } });
}

export async function resetPassword(token: string, newPassword: string) {
    return requestJson<{ token?: string; token_type?: string; detail?: string; message?: string }>("/auth/reset-password", {
        method: "POST",
        body: { token, new_password: newPassword },
    });
}

export async function verifyResetToken(token: string) {
    return requestJson<{ message?: string; user_id?: string; detail?: string }>(`/auth/reset-password/${token}`);
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
    return requestJson<ApiConversation>("/chat/conversations", {
        method: "POST",
        token,
        body: { title: title || "New Conversation" },
    });
}

export async function getAllConversations(token: string) {
    return requestJson<GetAllConversationsResponse>("/chat/conversations", { token, throwOnError: true });
}

export async function getConversation(conversationId: number, token: string) {
    return requestJson<ApiConversation>(`/chat/conversations/${conversationId}`, { token });
}

export async function updateConversation(conversationId: number, token: string, title: string) {
    return requestJson<ApiConversation>(`/chat/conversations/${conversationId}`, {
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
    return requestJson<ConversationMessagesResponse>(`/chat/conversations/${conversationId}/messages`, {
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
    const response = await fetch(`${getApiBaseUrl()}/chat/stream`, {
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
    return requestJson<ApiDocument>(`/documents/${docId}`, { method: "PUT", token, body: data });
}

export async function searchDocuments(query: string, token: string) {
    return requestJson<SearchDocumentsResponse>("/documents/search", { method: "POST", token, body: { query } });
}

export async function reindexDocument(docId: number, token: string) {
    return requestJson<DocumentStatusResponse>(`/documents/${docId}/reindex`, { method: "POST", token });
}

export async function getDocumentStatus(docId: number, token: string) {
    return requestJson<DocumentStatusResponse>(`/documents/status/${docId}`, { token });
}

// ============================================================================
// ADMIN APIs
// ============================================================================

// Admin types matching backend schemas
interface UsageStats {
    endpoint: string;
    total_calls: number;
    total_tokens: number;
    avg_latency: number;
}

interface SystemStats {
    total_users: number;
    total_documents: number;
    total_chats: number;
    total_api_calls: number;
    users_last_24h?: number;
    documents_last_24h?: number;
}

interface AdminStats {
    users: number;
    documents: number;
    chats: number;
    usage_today: number;
}

export type InvestigationIntent =
    | "investigate_root_cause"
    | "explain_low_confidence"
    | "draft_improved_answer"
    | "recommend_next_action";

export interface AdminInvestigationRunRequest {
    conversation_id: number;
    instruction_intent: InvestigationIntent;
    constraints?: string;
    k?: number;
}

export interface AdminInvestigationRunResponse {
    investigation_id: number;
    investigation_correlation_id?: string | null;
    conversation_id: number;
    instruction_intent: string;
    diagnosis: string;
    supporting_evidence: {
        retrieved_chunks: Array<Record<string, unknown>>;
        total_chunks_retrieved: number;
        document_ids: number[];
    };
    quality_summary: {
        confidence_score: number | null;
        hallucination_score: number | null;
        alignment_score: number | null;
    };
    recommended_next_actions: string[];
    improved_draft_answer?: string | null;
    error_details?: Array<Record<string, unknown>>;
    status: string;
    created_at: string;
}

export interface AdminInvestigationHistoryItem {
    id: number;
    instruction_intent: string;
    status: string;
    latency_ms: number;
    confidence_score: number | null;
    hallucination_score: number | null;
    alignment_score: number | null;
    diagnosis_summary: string;
    created_at: string;
}

export interface AdminInvestigationHistoryResponse {
    conversation_id: number;
    returned_count: number;
    items: AdminInvestigationHistoryItem[];
}

export async function getAdminUsers(token: string) {
    return requestJson<Record<string, unknown>[]>("/admin/users", { token });
}

export async function getAdminUsageStats(token: string) {
    return requestJson<UsageStats[]>("/admin/usage-stats", { token });
}

export async function getAdminSystemStats(token: string) {
    return requestJson<SystemStats>("/admin/system-stats", { token });
}

export async function getAdminUserUsage(userId: number, token: string) {
    return requestJson<Record<string, unknown>>(`/admin/users/${userId}/usage`, { token });
}

export async function getAdminDocuments(token: string) {
    return requestJson<Record<string, unknown>[]>("/admin/documents", { token });
}

export async function getAdminChats(token: string) {
    return requestJson<Record<string, unknown>[]>("/admin/chats", { token });
}

export async function getAdminStats(token: string) {
    return requestJson<AdminStats>("/admin/stats", { token });
}

export async function getAdminConversationDebug(conversationId: number, token: string) {
    return requestJson<Record<string, unknown>>(`/admin/debug/conversations/${conversationId}`, { token });
}

export async function runAdminInvestigation(body: AdminInvestigationRunRequest, token: string) {
    return requestJson<AdminInvestigationRunResponse>("/admin/investigations/run", {
        method: "POST",
        token,
        body,
        throwOnError: true,
    });
}

export async function getAdminInvestigationsByConversation(conversationId: number, token: string) {
    return requestJson<AdminInvestigationHistoryResponse>(`/admin/investigations/conversation/${conversationId}`, {
        token,
        throwOnError: true,
    });
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
