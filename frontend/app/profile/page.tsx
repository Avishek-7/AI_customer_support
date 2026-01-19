"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Navigation from "@/components/Navigation";
import { getCurrentUser, updateUser } from "@/lib/api";
import { authLogger } from "@/lib/logger";

type User = {
  id: number;
  name: string;
  email: string;
  role: string;
};

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const getToken = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  };

  useEffect(() => {
    const loadUser = async () => {
      const token = getToken();
      if (!token) {
        router.push("/login");
        return;
      }

      authLogger.info("Loading user profile");
      try {
        const response = await getCurrentUser(token);
        if (response.id) {
          setUser(response);
          setFormData({
            name: response.name || "",
            email: response.email || "",
            password: "",
            confirmPassword: "",
          });
          authLogger.info("User profile loaded", { userId: response.id });
        }
      } catch (err) {
        authLogger.error("Failed to load user profile", { error: String(err) });
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, [router]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getToken();
    if (!user || !token) return;

    // Validate
    if (!formData.name.trim() || !formData.email.trim()) {
      setMessage({ type: "error", text: "Name and email are required" });
      return;
    }

    if (formData.password && formData.password !== formData.confirmPassword) {
      setMessage({ type: "error", text: "Passwords do not match" });
      return;
    }

    setLoading(true);
    authLogger.info("Updating user profile", { userId: user.id });

    try {
      const updateData: Record<string, unknown> = {
        name: formData.name,
        email: formData.email,
      };

      if (formData.password) {
        updateData.password = formData.password;
      }

      const response = await updateUser(user.id, token, updateData);
      if (response.id) {
        setUser(response);
        setFormData({
          ...formData,
          password: "",
          confirmPassword: "",
        });
        setMessage({ type: "success", text: "Profile updated successfully" });
        authLogger.info("User profile updated", { userId: user.id });
        setIsEditing(false);
      } else if (response.detail) {
        setMessage({ type: "error", text: response.detail });
        authLogger.warn("Profile update failed", { error: response.detail });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Failed to update profile" });
      authLogger.error("Profile update error", { error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  if (loading && !user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p>Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-900 text-white">
      <Navigation />
      <div className="flex-1 p-6">
        <div className="max-w-md mx-auto bg-gray-800 rounded-lg p-8">
        <h1 className="text-3xl font-bold mb-8">My Profile</h1>

        {message && (
          <div
            className={`p-4 rounded mb-4 text-sm ${
              message.type === "success"
                ? "bg-green-900 text-green-200"
                : "bg-red-900 text-red-200"
            }`}
          >
            {message.text}
          </div>
        )}

        {!isEditing && user ? (
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-400">Name</label>
              <p className="text-lg font-semibold">{user.name}</p>
            </div>
            <div>
              <label className="text-sm text-gray-400">Email</label>
              <p className="text-lg font-semibold">{user.email}</p>
            </div>
            <div>
              <label className="text-sm text-gray-400">Role</label>
              <p className="text-lg font-semibold capitalize">{user.role}</p>
            </div>

            <div className="pt-4 flex gap-2">
              <button
                onClick={() => setIsEditing(true)}
                className="flex-1 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-semibold"
              >
                Edit Profile
              </button>
              {user.role === "admin" && (
                <button
                  onClick={() => router.push("/admin")}
                  className="flex-1 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded font-semibold"
                >
                  Admin Panel
                </button>
              )}
            </div>
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 rounded bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-2 rounded bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">New Password (optional)</label>
              <input
                type="password"
                placeholder="Leave blank to keep current password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-4 py-2 rounded bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Confirm Password</label>
              <input
                type="password"
                placeholder="Confirm new password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className="w-full px-4 py-2 rounded bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div className="flex gap-2 pt-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded font-semibold"
              >
                {loading ? "Saving..." : "Save Changes"}
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded font-semibold"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
      </div>
    </div>
  );
}
