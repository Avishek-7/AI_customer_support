"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "@/lib/api";
import { authLogger } from "@/lib/logger";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setMessage({ type: "error", text: "Please enter your email" });
      return;
    }

    setLoading(true);
    authLogger.info("Forgot password request", { email });

    try {
      const response = await forgotPassword(email);
      if (response.message) {
        setMessage({
          type: "success",
          text: "Password reset instructions have been sent to your email. Check your inbox for a reset link.",
        });
        authLogger.info("Forgot password request successful", { email });
        setEmail("");
      } else if (response.detail) {
        setMessage({ type: "error", text: response.detail });
        authLogger.warn("Forgot password request failed", { email, error: response.detail });
      }
    } catch (err) {
      setMessage({ type: "error", text: "An error occurred. Please try again." });
      authLogger.error("Forgot password error", { error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 p-8 rounded-lg w-full max-w-md space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Forgot Password?</h2>
          <p className="text-gray-400 text-sm mt-2">
            Enter your email address and we&apos;ll send you a link to reset your password.
          </p>
        </div>

        {message && (
          <div
            className={`p-4 rounded text-sm ${
              message.type === "success"
                ? "bg-green-900 text-green-200"
                : "bg-red-900 text-red-200"
            }`}
          >
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 rounded bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded py-2 font-semibold transition"
          >
            {loading ? "Sending..." : "Send Reset Link"}
          </button>
        </form>

        <div className="text-center text-sm text-gray-400">
          Remember your password?{" "}
          <Link href="/login" className="text-blue-400 hover:text-blue-300">
            Login here
          </Link>
        </div>
      </div>
    </div>
  );
}
