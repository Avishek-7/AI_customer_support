"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Navigation from "@/components/Navigation";
import { getStoredToken } from "@/lib/auth";
import {
  getAdminStats,
  getAdminSystemStats,
} from "@/lib/api";

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<Record<string, number | undefined> | null>(null);
  const [systemStats, setSystemStats] = useState<Record<string, number | undefined> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboard = async () => {
      const token = getStoredToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        setError(null);
        const [statsData, systemData] = await Promise.all([
          getAdminStats(token),
          getAdminSystemStats(token),
        ]) as [Record<string, number | undefined>, Record<string, number | undefined>];
        setStats(statsData);
        setSystemStats(systemData);
      } catch (err) {
        setError("Failed to load admin dashboard");
        console.error("Failed to load admin dashboard:", err);
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p>Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-900 text-white">
      <Navigation />
      <div className="flex-1 p-8">
        <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Admin Dashboard</h1>

        {error && (
          <div className="mb-6 rounded border border-red-700 bg-red-950/60 p-4">
            <p className="text-red-300">{error}</p>
            <button
              onClick={async () => {
                setLoading(true);
                setError(null);
                const token = getStoredToken();
                if (!token) {
                  router.push("/login");
                  return;
                }
                try {
                  const [statsData, systemData] = await Promise.all([
                    getAdminStats(token),
                    getAdminSystemStats(token),
                  ]) as [Record<string, number | undefined>, Record<string, number | undefined>];
                  setStats(statsData);
                  setSystemStats(systemData);
                } catch (retryErr) {
                  setError("Failed to load admin dashboard");
                  console.error("Admin dashboard retry failed:", retryErr);
                } finally {
                  setLoading(false);
                }
              }}
              className="mt-3 rounded bg-red-700 px-3 py-1 text-sm font-semibold hover:bg-red-600"
            >
              Retry
            </button>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-gradient-to-br from-blue-900 to-blue-700 p-6 rounded-lg">
            <p className="text-blue-200 text-sm font-semibold">Total Users</p>
            <p className="text-4xl font-bold mt-2">{stats?.users || 0}</p>
          </div>

          <div className="bg-gradient-to-br from-green-900 to-green-700 p-6 rounded-lg">
            <p className="text-green-200 text-sm font-semibold">Documents</p>
            <p className="text-4xl font-bold mt-2">{stats?.documents || 0}</p>
          </div>

          <div className="bg-gradient-to-br from-purple-900 to-purple-700 p-6 rounded-lg">
            <p className="text-purple-200 text-sm font-semibold">Total Chats</p>
            <p className="text-4xl font-bold mt-2">{stats?.chats || 0}</p>
          </div>

          <div className="bg-gradient-to-br from-orange-900 to-orange-700 p-6 rounded-lg">
            <p className="text-orange-200 text-sm font-semibold">API Calls Today</p>
            <p className="text-4xl font-bold mt-2">{stats?.usage_today || 0}</p>
          </div>
        </div>

        {/* System Stats */}
        {systemStats && (
          <div className="bg-gray-800 p-6 rounded-lg mb-8">
            <h2 className="text-2xl font-bold mb-4">System Statistics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-gray-400 text-sm">Total Users</p>
                <p className="text-2xl font-bold">{systemStats.total_users ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total Documents</p>
                <p className="text-2xl font-bold">{systemStats.total_documents ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total Chats</p>
                <p className="text-2xl font-bold">{systemStats.total_chats ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Total API Calls</p>
                <p className="text-2xl font-bold">{systemStats.total_api_calls ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Users (Last 24h)</p>
                <p className="text-2xl font-bold text-green-400">{systemStats.users_last_24h ?? 0}</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Documents (Last 24h)</p>
                <p className="text-2xl font-bold text-green-400">{systemStats.documents_last_24h ?? 0}</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation to other admin pages */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <button
            onClick={() => router.push("/admin/users")}
            className="bg-blue-600 hover:bg-blue-700 p-6 rounded-lg text-left transition"
          >
            <p className="font-semibold text-lg">👥 Users Management</p>
            <p className="text-sm text-blue-200 mt-2">Manage users and their roles</p>
          </button>

          <button
            onClick={() => router.push("/admin/analytics")}
            className="bg-green-600 hover:bg-green-700 p-6 rounded-lg text-left transition"
          >
            <p className="font-semibold text-lg">📊 Analytics</p>
            <p className="text-sm text-green-200 mt-2">View usage statistics and trends</p>
          </button>

          <button
            onClick={() => router.push("/admin/documents")}
            className="bg-purple-600 hover:bg-purple-700 p-6 rounded-lg text-left transition"
          >
            <p className="font-semibold text-lg">📄 Documents</p>
            <p className="text-sm text-purple-200 mt-2">Monitor all documents across users</p>
          </button>

          <button
            onClick={() => router.push("/admin/chats")}
            className="bg-orange-600 hover:bg-orange-700 p-6 rounded-lg text-left transition"
          >
            <p className="font-semibold text-lg">💬 Chats</p>
            <p className="text-sm text-orange-200 mt-2">View recent chat activities</p>
          </button>

          <button
            onClick={() => router.push("/admin/debug")}
            className="bg-red-600 hover:bg-red-700 p-6 rounded-lg text-left transition"
          >
            <p className="font-semibold text-lg">🔧 Debug</p>
            <p className="text-sm text-red-200 mt-2">Debug conversations and RAG pipeline</p>
          </button>
        </div>
        </div>
      </div>
    </div>
  );
}
