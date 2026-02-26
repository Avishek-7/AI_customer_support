// components/ChatBubble.tsx
"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

type Source = { title?: string; document_id?: number; chunk_id?: number };

export default function ChatBubble({
  role,
  content,
  sources = [],
}: {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}) {
  const isUser = role === "user";

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[78%] ${isUser ? "text-white" : "text-gray-100"}`}>
        <div className={`flex items-start gap-3`}>
          {/* Avatar */}
          <div className="flex-none">
            {isUser ? (
              <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center font-semibold">U</div>
            ) : (
              <div className="w-9 h-9 rounded-full bg-gray-700 flex items-center justify-center font-semibold">AI</div>
            )}
          </div>

          {/* Bubble */}
          <div className={`${isUser ? "bg-blue-600" : "bg-gray-800"} p-4 rounded-2xl whitespace-pre-wrap`}>
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code({ className, children, ...props }) {
                    const isBlock = Boolean(className && className.includes("language-"));
                    if (isBlock) {
                      return (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }
                    return (
                      <code className="bg-gray-900 px-1.5 py-0.5 rounded text-sm" {...props}>
                        {children}
                      </code>
                    );
                  },
                  pre({ children }) {
                    const childArray = React.Children.toArray(children);
                    const firstChild = childArray[0];
                    const isCodeElement = React.isValidElement(firstChild) && firstChild.type === "code";

                    if (isCodeElement) {
                      const className = (firstChild.props as { className?: string }).className || "";
                      const match = /language-(\w+)/.exec(className);
                      const lang = match ? match[1] : "";
                      const codeText = String((firstChild.props as { children?: React.ReactNode }).children ?? "");
                      return (
                        <SyntaxHighlighter
                          style={oneDark as { [key: string]: React.CSSProperties }}
                          language={lang}
                          PreTag="div"
                        >
                          {codeText.replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      );
                    }

                    return <pre className="overflow-x-auto">{children}</pre>;
                  },
                }}
              >
                {content || ""}
              </ReactMarkdown>
            </div>

            {/* Sources */}
            {!isUser && sources && sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-700 text-xs text-gray-300 space-y-1">
                <div className="font-medium text-sm text-gray-200">Sources</div>
                {sources.map((s, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="opacity-80">📄</span>
                    <span className="truncate">
                      {s.title ?? `Document ${s.document_id}`} {s.chunk_id !== undefined && `(chunk ${s.chunk_id})`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

