export async function streamChat(
    message: string,
    conversationId: number,
    token: string,
    cb: (chunk: string) => void,
    documentIds?: number[]
) {
    const response = await fetch("/chat/stream", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            message,
            conversation_id: conversationId,
            document_ids: documentIds,
        }),
    });

    if (!response.ok) {
        const errorBody = await response.text().catch(() => "");
        throw new Error(`Chat stream request failed (${response.status}): ${errorBody || response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
        throw new Error("Chat stream response body is empty");
    }

    const decoder = new TextDecoder();

    try {
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;

            if (value) {
                cb(decoder.decode(value, { stream: true }));
            }
        }

        const remaining = decoder.decode();
        if (remaining) {
            cb(remaining);
        }
    } finally {
        reader.releaseLock();
    }
}