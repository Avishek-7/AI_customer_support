export async function streamChat(message: string, token: string, cb:(chunk:string)=>void) {
    const response = await fetch("/chat/stream", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const {done, value} = await reader!.read();
        if (done) break;

        cb(decoder.decode(value));
    }
}