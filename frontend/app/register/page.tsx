"use client";

import { useState } from "react";
import { authLogger } from "@/lib/logger";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const emailFingerprint = async (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (!normalized || typeof window === "undefined" || !window.crypto?.subtle) return "unavailable";
    const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(normalized));
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
  };

  const register = async () => {
    const emailHash = await emailFingerprint(email);
    if (password !== confirmPassword) {
      authLogger.warn("Registration failed - password mismatch", { emailHash });
      alert("Passwords do not match");
      return;
    }

    authLogger.info("Registration attempt", { emailHash, username });

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: username })
      });

      if (!response.ok) {
        const fallback = await response.text();
        let detail = fallback || `Registration failed (${response.status})`;
        try {
          const parsed = JSON.parse(fallback || "{}");
          if (parsed?.detail) detail = parsed.detail;
        } catch {
          // Keep text fallback
        }
        authLogger.warn("Registration failed", { emailHash, status: response.status, error: detail });
        alert(detail);
        return;
      }

      let data: Record<string, unknown> = {};
      try {
        data = await response.json();
      } catch (parseErr) {
        authLogger.error("Registration response parse error", { emailHash, error: String(parseErr) });
        alert("Registration failed: invalid server response");
        return;
      }

      authLogger.debug("Registration response received", { status: response.status, hasToken: !!data.token });

      if (data.token) {
        authLogger.info("Registration successful", { emailHash });
        localStorage.setItem("token", String(data.token));
        alert("Registration successful!");
        window.location.href = "/chat";
      } else if (data.detail) {
        authLogger.warn("Registration failed", { emailHash, error: String(data.detail) });
        alert(String(data.detail));
      }
    } catch (err) {
      authLogger.error("Registration network failure", { emailHash, error: String(err) });
      alert("Unable to register right now. Please try again.");
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 p-6 rounded-lg w-80 space-y-4">
        <h2 className="text-xl font-semibold">Register</h2>

        <label htmlFor="register-username" className="block text-sm">Username</label>

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          id="register-username"
          aria-required="true"
          placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />

        <label htmlFor="register-email" className="block text-sm">Email</label>

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          id="register-email"
          type="email"
          aria-required="true"
          placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />

        <label htmlFor="register-password" className="block text-sm">Password</label>

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          id="register-password"
          aria-required="true"
          type="password" placeholder="Password"
          value={password} onChange={e => setPassword(e.target.value)} />

        <label htmlFor="register-confirm-password" className="block text-sm">Confirm Password</label>
        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          id="register-confirm-password"
          aria-required="true"
          type="password" placeholder="Confirm Password"
          value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />

        <button onClick={register}
          className="w-full bg-blue-600 hover:bg-blue-700 rounded py-2">
          Register
        </button>

      </div>
    </div>
  )

}
