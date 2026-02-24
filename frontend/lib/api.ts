/**
 * Comprehensive API client for all backend endpoints
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_URL is required for frontend API client");
}

// ============================================================================
// AUTHENTICATION APIs
// ============================================================================

export async function forgotPassword(email: string) {
    const response = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
    });
    return response.json();
}

export async function resetPassword(token: string, newPassword: string) {
    const response = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: newPassword }),
    });
    return response.json();
}

export async function verifyResetToken(token: string) {
    const response = await fetch(`${API_BASE}/auth/reset-password/${token}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
    });
    return response.json();
}

// ============================================================================
// USER APIs
// ============================================================================

export async function getCurrentUser(token: string) {
    const response = await fetch(`${API_BASE}/users/me`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function updateUser(userId: number, token: string, data: {
    name?: string;
    email?: string;
    password?: string;
    role?: string;
}) {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });
    return response.json();
}

export async function getAllUsers(token: string) {
    const response = await fetch(`${API_BASE}/users/`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getUser(userId: number, token: string) {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function createUser(token: string, data: {
    email: string;
    password: string;
    name?: string;
    role?: string;
}) {
    const response = await fetch(`${API_BASE}/users/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });
    return response.json();
}

export async function deleteUser(userId: number, token: string) {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` },
    });
    if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        throw new Error(`Failed to delete user (${response.status}): ${errorText || response.statusText}`);
    }

    if (response.status === 204) {
        return null;
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return response.json();
    }

    const text = await response.text().catch(() => "");
    return text || null;
}

// ============================================================================
// CONVERSATION APIs
// ============================================================================

export async function createConversation(token: string, title?: string) {
    const response = await fetch(`${API_BASE}/chat/conversations`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ title: title || "New Conversation" }),
    });
    return response.json();
}

export async function getAllConversations(token: string) {
    const response = await fetch(`${API_BASE}/chat/conversations`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    if (!response.ok) {
        throw new Error(`Failed to load conversations (${response.status})`);
    }
    return response.json();
}

export async function getConversation(conversationId: number, token: string) {
    const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function updateConversation(conversationId: number, token: string, title: string) {
    const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ title }),
    });
    return response.json();
}

export async function deleteConversation(conversationId: number, token: string) {
    const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` },
    });
    if (response.status === 204) {
        return null;
    }
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        return response.json();
    }
    const text = await response.text().catch(() => "");
    return text || null;
}

export async function getConversationMessages(conversationId: number, token: string) {
    const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}/messages`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    
    if (!response.ok) {
        const error = await response.text();
        console.error(`Failed to get conversation messages: ${response.status}`, error);
        throw new Error(`Failed to load conversation: ${response.status} - ${error}`);
    }
    
    return response.json();
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
    const response = await fetch(`${API_BASE}/chat/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
            message,
            conversation_id: conversationId,
            ...(data?.system_prompt && { system_prompt: data.system_prompt }),
            ...(data?.document_ids && { document_ids: data.document_ids }),
        }),
    });
    return response.json();
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
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
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
    const response = await fetch(`${API_BASE}/documents/${docId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(data),
    });
    return response.json();
}

export async function searchDocuments(query: string, token: string) {
    const response = await fetch(`${API_BASE}/documents/search`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ query }),
    });
    return response.json();
}

export async function reindexDocument(docId: number, token: string) {
    const response = await fetch(`${API_BASE}/documents/${docId}/reindex`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getDocumentStatus(docId: number, token: string) {
    const response = await fetch(`${API_BASE}/documents/status/${docId}`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

// ============================================================================
// ADMIN APIs
// ============================================================================

export async function getAdminUsers(token: string) {
    const response = await fetch(`${API_BASE}/admin/users`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminUsageStats(token: string) {
    const response = await fetch(`${API_BASE}/admin/usage-stats`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminSystemStats(token: string) {
    const response = await fetch(`${API_BASE}/admin/system-stats`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminUserUsage(userId: number, token: string) {
    const response = await fetch(`${API_BASE}/admin/users/${userId}/usage`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminDocuments(token: string) {
    const response = await fetch(`${API_BASE}/admin/documents`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminChats(token: string) {
    const response = await fetch(`${API_BASE}/admin/chats`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminStats(token: string) {
    const response = await fetch(`${API_BASE}/admin/stats`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

export async function getAdminConversationDebug(conversationId: number, token: string) {
    const response = await fetch(`${API_BASE}/admin/debug/conversations/${conversationId}`, {
        headers: { "Authorization": `Bearer ${token}` },
    });
    return response.json();
}

// ============================================================================
// VECTOR APIs
// ============================================================================

export async function getVectorMetadata(docId: number) {
    const response = await fetch(`${API_BASE}/vectors/document/${docId}`);
    return response.json();
}

export async function getVectorStats() {
    const response = await fetch(`${API_BASE}/vectors/stats`);
    return response.json();
}
