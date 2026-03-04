// components/TypingDots.tsx
export default function TypingDots({ className = "" }: { className?: string }) {
  return (
    <div role="status" aria-live="polite" className={`flex items-center gap-1 ${className}`}>
      <span className="sr-only">Typing…</span>
      <span aria-hidden="true" className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: "0s" }} />
      <span aria-hidden="true" className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: "0.15s" }} />
      <span aria-hidden="true" className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: "0.3s" }} />
    </div>
  );
}

