interface Props {
    role: "user" | "assistant";
    content: string;
    sources?: { title: string; chunk_id: number }[];
}

export default function ChatBubble({ role, content, sources }: Props) {
    const isUser = role === "user";

    return (
        <div className={`flex w-full ${isUser ? "justify-end": "justify-start"} mb-2`}>
            <div className={`px-4 py-2 rounded-xl max-w-[70%] whitespace-pre-wrap
                ${isUser ? "bg-blue-600 text-white" : "bg-gray-800"}`}>
                    <p>{content}</p>

                    {/* ----- Sources Section ------*/}
                    {!isUser && sources && sources.length > 0 && (
                        <div className="mt-2 text-xs text-gray-300 border-t border-gray-700 pt-1 space-y-1">
                            <strong>Sources:</strong>
                            {sources.map((src, i) => (
                                <div key={i} className="opacity-70">
                                    {src.title} {src.chunk_id !== undefined && `(chunk ${src.chunk_id})`}
                                </div>
                            ))}
                        </div>
                    )}
            </div>
        </div>
    );
}