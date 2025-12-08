interface Props {
    role: "user" | "assistant";
    content: string;
}

export default function ChatBubble({ role, content }: Props) {
    const isUser = role === "user";

    return (
        <div className={`flex w-full ${isUser ? "justify-end": "justify-start"}`}>
            <div className={`px-4 py-2 rounded-xl max-w-[75%] whitespace-pre-wrap
                ${isUser ? "bg-blue-600 text-white" : "bg-gray-700"}`}>
                    {content}
                </div>
        </div>
    );
}