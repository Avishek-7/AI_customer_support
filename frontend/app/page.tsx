"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStoredToken } from "@/lib/auth";

export default function Page() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      // Redirect to chat if already logged in
      window.location.href = "/chat";
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-gray-900 to-black text-white flex flex-col items-center justify-center">
      <div className="text-center">
        <h1 className="text-5xl font-bold mb-4">AI Customer Support</h1>
        <p className="text-xl mb-8 text-gray-300">Smart document-based Q&A with LLM</p>
        
        {!isAuthenticated ? (
          <div className="flex gap-4 justify-center">
            <Link href="/login" className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold inline-block">
              Login
            </Link>
            <Link href="/register" className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-semibold inline-block">
              Register
            </Link>
          </div>
        ) : (
          <p>Redirecting to chat...</p>
        )}
      </div>
    </div>
  );
}
