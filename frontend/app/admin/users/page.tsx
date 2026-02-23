"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAdminUsers, createUser, deleteUser } from "@/lib/api";

type AdminUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  document_count: number;
  chat_count: number;
  total_api_calls: number;
};

export default function AdminUsersPage() {
  const router = useRouter();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUserData, setNewUserData] = useState({
    email: "",
    password: "",
    name: "",
    role: "user",
  });

  const getToken = () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  };

  const reloadUsers = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getAdminUsers(token);
      setUsers(data || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message || "Failed to load users");
      setUsers([]);
      console.error("Failed to load users:", err);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    reloadUsers();
  }, [reloadUsers]);

  const handleCreateUser = async () => {
    if (isCreating) return;
    const token = getToken();
    if (!token) return;

    if (!newUserData.email || !newUserData.password) {
      alert("Email and password are required");
      return;
    }

    setIsCreating(true);
    try {
      await createUser(token, newUserData);
      const data = await getAdminUsers(token);
      setUsers(data || []);
      setShowCreateForm(false);
      setNewUserData({ email: "", password: "", name: "", role: "user" });
    } catch (err) {
      alert("Failed to create user: " + String(err));
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    const token = getToken();
    if (!token) return;

    if (!confirm("Are you sure you want to delete this user?")) return;

    try {
      await deleteUser(userId, token);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      alert("Failed to delete user: " + String(err));
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link href="/admin" className="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
              ← Back to Admin
            </Link>
            <h1 className="text-4xl font-bold">Users Management</h1>
          </div>
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-semibold"
          >
            + Create User
          </button>
        </div>

        {/* Create User Form */}
        {showCreateForm && (
          <div className="bg-gray-800 p-6 rounded-lg mb-8">
            <h2 className="text-xl font-bold mb-4">Create New User</h2>
            <div className="space-y-4">
              <label htmlFor="new-user-email" className="block text-sm font-medium">Email</label>
              <input
                id="new-user-email"
                type="email"
                placeholder="Email"
                value={newUserData.email}
                onChange={(e) => setNewUserData({ ...newUserData, email: e.target.value })}
                className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
              />
              <label htmlFor="new-user-name" className="block text-sm font-medium">Full Name</label>
              <input
                id="new-user-name"
                type="text"
                placeholder="Full Name (optional)"
                value={newUserData.name}
                onChange={(e) => setNewUserData({ ...newUserData, name: e.target.value })}
                className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
              />
              <label htmlFor="new-user-password" className="block text-sm font-medium">Password</label>
              <input
                id="new-user-password"
                type="password"
                autoComplete="new-password"
                placeholder="Password"
                value={newUserData.password}
                onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}
                className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
              />
              <label htmlFor="new-user-role" className="block text-sm font-medium">Role</label>
              <select
                id="new-user-role"
                value={newUserData.role}
                onChange={(e) => setNewUserData({ ...newUserData, role: e.target.value })}
                className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <div className="flex gap-2">
                <button
                  onClick={handleCreateUser}
                  disabled={isCreating}
                  className="px-4 py-2 rounded bg-green-600 hover:bg-green-700 font-semibold"
                >
                  {isCreating ? "Creating..." : "Create"}
                </button>
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 rounded bg-gray-600 hover:bg-gray-500 font-semibold"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Users Table */}
        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            {error && (
              <div className="px-4 py-3 text-sm text-red-300 bg-red-950/50 border-b border-red-800">
                <p>{error}</p>
                <button onClick={reloadUsers} className="mt-2 rounded bg-red-700 px-3 py-1 text-xs font-semibold hover:bg-red-600">
                  Retry
                </button>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Name</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Email</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">Role</th>
                    <th className="px-6 py-3 text-center text-sm font-semibold">Documents</th>
                    <th className="px-6 py-3 text-center text-sm font-semibold">Chats</th>
                    <th className="px-6 py-3 text-center text-sm font-semibold">API Calls</th>
                    <th className="px-6 py-3 text-center text-sm font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-700 transition">
                      <td className="px-6 py-4 font-medium">{user.name || "N/A"}</td>
                      <td className="px-6 py-4 text-sm text-gray-300">{user.email}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          user.role === "admin"
                            ? "bg-purple-600 text-purple-200"
                            : "bg-blue-600 text-blue-200"
                        }`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">{user.document_count}</td>
                      <td className="px-6 py-4 text-center">{user.chat_count}</td>
                      <td className="px-6 py-4 text-center">{user.total_api_calls}</td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => router.push(`/admin/users/${user.id}`)}
                          className="px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-xs font-semibold"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user.id)}
                          className="px-2 py-1 rounded bg-red-600 hover:bg-red-700 text-xs font-semibold"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
