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

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const {done, value} = await reader!.read();
        if (done) break;

        cb(decoder.decode(value));
    }
}