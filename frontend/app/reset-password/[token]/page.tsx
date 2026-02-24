"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { resetPassword, verifyResetToken } from "@/lib/api";
import { authLogger } from "@/lib/logger";

export default function ResetPasswordPage() {
  const params = useParams();
  const router = useRouter();
  const tokenParam = params?.token;
  const token = typeof tokenParam === "string" && !Array.isArray(tokenParam) ? tokenParam : null;

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(true);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const redirectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!token) {
      setVerifying(false);
      setMessage({ type: "error", text: "Invalid reset token" });
      return;
    }

    let isMounted = true;
    let redirectTimer: ReturnType<typeof setTimeout> | null = null;

    const verifyToken = async () => {
      authLogger.info("Verifying reset token");
      try {
        const response = await verifyResetToken(token);
        if (!isMounted) return;
        if (response.message) {
          authLogger.info("Reset token verified successfully", { userId: response.user_id });
          setVerifying(false);
        } else if (response.detail) {
          setMessage({ type: "error", text: "Invalid or expired reset token" });
          setVerifying(false);
          authLogger.warn("Invalid reset token", { error: response.detail });
          redirectTimer = setTimeout(() => router.push("/login"), 3000);
        } else {
          setVerifying(false);
          setMessage({ type: "error", text: "Unexpected response from server" });
          authLogger.warn("Unexpected reset token verification response shape", { response });
          redirectTimer = setTimeout(() => router.push("/login"), 3000);
        }
      } catch (err) {
        if (!isMounted) return;
        setMessage({ type: "error", text: "Failed to verify token" });
        setVerifying(false);
        authLogger.error("Token verification error", { error: String(err) });
        redirectTimer = setTimeout(() => router.push("/login"), 3000);
      }
    };

    verifyToken();

    return () => {
      isMounted = false;
      if (redirectTimer) {
        clearTimeout(redirectTimer);
      }
    };
  }, [token, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      setMessage({ type: "error", text: "Invalid reset token" });
      return;
    }

    if (!password.trim() || !confirmPassword.trim()) {
      setMessage({ type: "error", text: "Please fill in all fields" });
      return;
    }

    if (password !== confirmPassword) {
      setMessage({ type: "error", text: "Passwords do not match" });
      return;
    }

    if (password.length < 8) {
      setMessage({ type: "error", text: "Password must be at least 8 characters long" });
      return;
    }

    setLoading(true);
    authLogger.info("Attempting password reset");

    try {
      const response = await resetPassword(token, password);
      if (response.token) {
        authLogger.info("Password reset successful");
        setMessage({
          type: "success",
          text: "Password reset successfully! Redirecting to chat...",
        });
        localStorage.setItem("token", response.token);
        redirectTimeoutRef.current = setTimeout(() => router.push("/chat"), 2000);
      } else if (response.detail) {
        setMessage({ type: "error", text: response.detail });
        authLogger.warn("Password reset failed", { error: response.detail });
      } else {
        setMessage({ type: "error", text: "Unexpected response from server" });
        authLogger.warn("Password reset returned unexpected response shape", { response });
      }
    } catch (err) {
      setMessage({ type: "error", text: "An error occurred. Please try again." });
      authLogger.error("Password reset error", { error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
        redirectTimeoutRef.current = null;
      }
    };
  }, []);

  if (verifying) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p>Verifying reset token...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 p-8 rounded-lg w-full max-w-md space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Reset Password</h2>
          <p className="text-gray-400 text-sm mt-2">Enter your new password below</p>
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
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium mb-2">New Password</label>
            <input
              id="new-password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 rounded bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium mb-2">Confirm Password</label>
            <input
              id="confirm-password"
              type="password"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 rounded bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded py-2 font-semibold transition"
          >
            {loading ? "Resetting..." : "Reset Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
