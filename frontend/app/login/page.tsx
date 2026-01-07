"use client";

import { useState } from "react";
import { authLogger } from "@/lib/logger";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL;

  const login = async () => {
    authLogger.info("Login attempt", { email });

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();
    authLogger.debug("Login response received", { status: response.status, hasToken: !!data.token });

    if (data.token) {
      authLogger.info("Login successful", { email });
      localStorage.setItem("token", data.token);
      window.location.href = "/chat";
    } else if (data.detail) {
      authLogger.warn("Login failed", { email, error: data.detail });
      alert(data.detail);
    } else {
      authLogger.error("Login failed - unknown error", { email });
      alert("Login failed");
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 p-6 rounded-lg w-80 space-y-4">
        <h2 className="text-xl font-semibold">Login</h2>

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          type="password" placeholder="Password"
          value={password} onChange={e => setPassword(e.target.value)} />

        <button onClick={login}
          className="w-full bg-blue-600 hover:bg-blue-700 rounded py-2">
          Login
        </button>
      </div>
    </div>
  )
}
