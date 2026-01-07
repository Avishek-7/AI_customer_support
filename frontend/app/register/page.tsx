"use client";

import { useState } from "react";
import { authLogger } from "@/lib/logger";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const register = async () => {
    if (password !== confirmPassword) {
      authLogger.warn("Registration failed - password mismatch", { email });
      alert("Passwords do not match");
      return;
    }

    authLogger.info("Registration attempt", { email, username });

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: username })
    });

    const data = await response.json();
    authLogger.debug("Registration response received", { status: response.status, hasToken: !!data.token });

    if (data.token) {
      authLogger.info("Registration successful", { email });
      localStorage.setItem("token", data.token);
      alert("Registration successful!");
      window.location.href = "/chat";
    } else if (data.detail) {
      authLogger.warn("Registration failed", { email, error: data.detail });
      alert(data.detail);
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 p-6 rounded-lg w-80 space-y-4">
        <h2 className="text-xl font-semibold">Register</h2>

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />

        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
          type="password" placeholder="Password"
          value={password} onChange={e => setPassword(e.target.value)} />
        <input className="w-full px-2 py-2 rounded bg-gray-700 text-white"
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
