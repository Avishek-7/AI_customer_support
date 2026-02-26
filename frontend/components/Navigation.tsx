"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { clearStoredToken, getAuthHeaders, getStoredToken } from "@/lib/auth";
import { getApiBase } from "@/lib/runtimeEnv";

export default function Navigation() {
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const token = getStoredToken();
    const apiBase = getApiBase();
    if (!token || !apiBase) {
      setIsAdmin(false);
      return;
    }

    const controller = new AbortController();

    (async () => {
      try {
        const response = await fetch(`${apiBase}/users/me`, {
          headers: getAuthHeaders(token),
          signal: controller.signal,
        });
        if (!response.ok) {
          setIsAdmin(false);
          return;
        }
        const user = await response.json();
        setIsAdmin(user?.role === "admin");
      } catch {
        setIsAdmin(false);
      }
    })();

    return () => controller.abort();
  }, []);

  return (
    <nav className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
      <Link href="/chat" className="text-xl font-bold text-blue-400 hover:text-blue-300">
        AI Customer Support
      </Link>
      
      <div className="flex gap-4 items-center">
        <Link href="/profile" aria-label="Profile" className="hover:text-blue-300 transition">
          👤 Profile
        </Link>
        <Link href="/documents" aria-label="Documents" className="hover:text-blue-300 transition">
          📄 Documents
        </Link>
        {isAdmin && (
          <Link href="/admin" aria-label="Admin" className="hover:text-blue-300 transition">
            ⚙️ Admin
          </Link>
        )}
        <button
          onClick={() => {
            clearStoredToken();
            window.location.href = "/login";
          }}
          className="px-3 py-1 rounded bg-red-600 hover:bg-red-700 text-sm font-semibold"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
