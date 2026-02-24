"use client";

import { useState } from "react";
import { authLogger } from "@/lib/logger";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

  const safeEmailFingerprint = async (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (!normalized || typeof window === "undefined" || !window.crypto?.subtle) return "unavailable";
    const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(normalized));
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  };

  const login = async () => {
    const emailHash = await safeEmailFingerprint(email);
    authLogger.info("Login attempt", { emailHash });

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password })
      });
      const responseClone = response.clone();

      if (!response.ok) {
        let errorText = `Login failed (${response.status})`;
        try {
          const errData = await response.json();
          errorText = errData?.detail || errorText;
        } catch {
          const text = await responseClone.text();
          if (text) errorText = text;
        }
        authLogger.warn("Login failed", { status: response.status, error: errorText });
        alert(errorText);
        return;
      }

      let data: Record<string, unknown> = {};
      try {
        data = await response.json();
      } catch (parseErr) {
        authLogger.error("Login response parse failed", { emailHash, error: String(parseErr) });
        alert("Login failed. Invalid server response.");
        return;
      }

      authLogger.debug("Login response received", { status: response.status, hasToken: !!data.token });

      if (data.token) {
        authLogger.info("Login successful", { emailHash });
        localStorage.setItem("token", "__cookie_session__");
        window.location.href = "/chat";
      } else {
        authLogger.error("Login failed - missing token", { emailHash });
        alert("Login failed");
      }
    } catch (err) {
      authLogger.error("Login request failed", { emailHash, error: String(err) });
      alert("Unable to login right now. Please try again.");
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    login();
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 p-6 rounded-lg w-80 space-y-4">
        <h2 className="text-xl font-semibold">Login</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label htmlFor="login-email" className="sr-only">Email</label>
          <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
            id="login-email"
            type="email"
            autoComplete="email"
            placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />

          <label htmlFor="login-password" className="sr-only">Password</label>
          <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
            id="login-password"
            type="password" placeholder="Password"
            autoComplete="current-password"
            value={password} onChange={e => setPassword(e.target.value)} />

          <button type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 rounded py-2">
            Login
          </button>
        </form>

        <div className="text-center text-sm space-y-2">
          <div>
            <a href="/forgot-password" className="text-blue-400 hover:text-blue-300">
              Forgot password?
            </a>
          </div>
          <div>
            Don&apos;t have an account?{" "}
            <a href="/register" className="text-blue-400 hover:text-blue-300">
              Register
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
