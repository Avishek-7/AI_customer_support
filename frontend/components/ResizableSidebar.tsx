// components/ResizableSidebar.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface ResizableSidebarProps {
  children: React.ReactNode;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  side?: "left" | "right";
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function ResizableSidebar({
  children,
  defaultWidth = 260,
  minWidth = 200,
  maxWidth = 520,
  side = "left",
  collapsed,
  onCollapsedChange,
}: ResizableSidebarProps) {
  const [width, setWidth] = useState<number>(defaultWidth);
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const dragging = useRef(false);
  const sidebarRef = useRef<HTMLDivElement>(null);

  const isCollapsed = collapsed ?? internalCollapsed;

  const setCollapsed = (next: boolean) => {
    if (collapsed === undefined) {
      setInternalCollapsed(next);
    }
    onCollapsedChange?.(next);
  };

  function onMouseDown() {
    dragging.current = true;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  }

  function onMouseUp() {
    dragging.current = false;
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
  }

  // attach global listeners
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;

      if (!sidebarRef.current) return;

      const rect = sidebarRef.current.getBoundingClientRect();
      let newWidth: number;

      if (side === "left") {
        newWidth = e.clientX - rect.left;
      } else {
        newWidth = rect.right - e.clientX;
      }

      newWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
      setWidth(newWidth);
    };

    window.addEventListener("mouseup", onMouseUp);
    window.addEventListener("mousemove", onMouseMove);

    return () => {
      window.removeEventListener("mouseup", onMouseUp);
      window.removeEventListener("mousemove", onMouseMove);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      dragging.current = false;
    };
  }, [maxWidth, minWidth, side]);

  return (
    <div
      ref={sidebarRef}
      style={{
        width: isCollapsed ? "50px" : `${width}px`,
        transition: "width 0.3s ease-in-out",
      }}
      className="bg-gray-900 border-r border-gray-800 flex flex-col relative overflow-hidden"
    >
      {/* Toggle Button */}
      <button
        onClick={() => setCollapsed(!isCollapsed)}
        className="absolute top-4 right-2 z-50 p-1 hover:bg-gray-700 rounded transition-colors"
        title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {isCollapsed ? (
          side === "right" ? <ChevronLeft className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />
        ) : (
          side === "right" ? <ChevronRight className="w-5 h-5 text-gray-400" /> : <ChevronLeft className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {/* Content */}
      {!isCollapsed && <div className="p-4 flex flex-col flex-1 overflow-hidden">{children}</div>}

      {/* Resize Handle */}
      <div
        className={`${side === "left" ? "right-0" : "left-0"} absolute top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 hover:opacity-50 transition-opacity`}
        onMouseDown={onMouseDown}
      />
    </div>
  );
}

