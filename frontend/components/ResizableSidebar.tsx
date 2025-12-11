// components/ResizableSidebar.tsx
"use client";

import { useState, useRef } from "react";

export default function ResizableSidebar({ children }: { children: React.ReactNode }) {
  const [width, setWidth] = useState<number>(260);
  const dragging = useRef(false);

  function onMouseDown() {
    dragging.current = true;
    document.body.style.userSelect = "none";
  }

  function onMouseUp() {
    dragging.current = false;
    document.body.style.userSelect = "";
  }

  function onMouseMove(e: MouseEvent) {
    if (!dragging.current) return;
    const newWidth = Math.max(200, Math.min(520, e.clientX));
    setWidth(newWidth);
  }

  // attach global listeners
  if (typeof window !== "undefined") {
    window.onmouseup = onMouseUp;
    window.onmousemove = onMouseMove;
  }

  return (
    <aside style={{ width }} className="bg-gray-900 border-r border-gray-800 p-4 flex flex-col">
      {children}
      <div
        className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize"
        onMouseDown={onMouseDown}
        style={{ transform: "translateX(0)" }}
      />
    </aside>
  );
}

