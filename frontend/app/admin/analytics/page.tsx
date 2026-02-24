"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getAdminUsageStats, getAdminSystemStats } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

export default function AdminAnalyticsPage() {
  const router = useRouter();
  const [usageStats, setUsageStats] = useState<Array<Record<string, unknown>>>([]);
  const [systemStats, setSystemStats] = useState<Record<string, number | undefined> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAnalytics = async () => {
      const token = getStoredToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        setError(null);
        const [usage, system] = await Promise.all([
          getAdminUsageStats(token),
          getAdminSystemStats(token),
        ]) as [Array<Record<string, unknown>>, Record<string, number | undefined>];
        setUsageStats(usage || []);
        setSystemStats(system);
      } catch (err) {
        setError("Failed to load analytics");
        console.error("Failed to load analytics:", err);
      } finally {
        setLoading(false);
      }
    };

    loadAnalytics();
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/admin" className="text-blue-400 hover:text-blue-300 text-sm mb-4 inline-block">
          ← Back to Admin
        </Link>
        <h1 className="text-4xl font-bold mb-8">Analytics & Statistics</h1>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className="space-y-8">
            {error && <p className="text-red-400">{error}</p>}
            {/* System Overview */}
            {systemStats && (
              <div className="bg-gray-800 p-6 rounded-lg">
                <h2 className="text-2xl font-bold mb-4">System Overview</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-700 p-4 rounded">
                    <p className="text-gray-300 text-sm">Total Users</p>
                    <p className="text-3xl font-bold text-blue-400">{systemStats.total_users}</p>
                  </div>
                  <div className="bg-gray-700 p-4 rounded">
                    <p className="text-gray-300 text-sm">Total Documents</p>
                    <p className="text-3xl font-bold text-green-400">{systemStats.total_documents}</p>
                  </div>
                  <div className="bg-gray-700 p-4 rounded">
                    <p className="text-gray-300 text-sm">Total Chats</p>
                    <p className="text-3xl font-bold text-purple-400">{systemStats.total_chats}</p>
                  </div>
                  <div className="bg-gray-700 p-4 rounded">
                    <p className="text-gray-300 text-sm">Total API Calls</p>
                    <p className="text-3xl font-bold text-orange-400">{systemStats.total_api_calls}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Activity Last 24 Hours */}
            {systemStats && (
              <div className="bg-gray-800 p-6 rounded-lg">
                <h2 className="text-2xl font-bold mb-4">Activity (Last 24 Hours)</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-blue-900 p-4 rounded">
                    <p className="text-blue-200 text-sm">New Users</p>
                    <p className="text-2xl font-bold">{systemStats.users_last_24h}</p>
                  </div>
                  <div className="bg-green-900 p-4 rounded">
                    <p className="text-green-200 text-sm">New Documents</p>
                    <p className="text-2xl font-bold">{systemStats.documents_last_24h}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Endpoint Usage Stats */}
            {usageStats.length > 0 && (
              <div className="bg-gray-800 p-6 rounded-lg">
                <h2 className="text-2xl font-bold mb-4">API Endpoint Usage</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-2 text-left">Endpoint</th>
                        <th className="px-4 py-2 text-center">Calls</th>
                        <th className="px-4 py-2 text-center">Tokens</th>
                        <th className="px-4 py-2 text-center">Avg Latency (ms)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {usageStats.map((stat, idx) => (
                        <tr key={idx} className="hover:bg-gray-700 transition">
                          <td className="px-4 py-2 font-mono text-blue-300">{String(stat.endpoint ?? "-")}</td>
                          <td className="px-4 py-2 text-center">{String(stat.total_calls ?? 0)}</td>
                          <td className="px-4 py-2 text-center">{String(stat.total_tokens ?? 0)}</td>
                          <td className="px-4 py-2 text-center">{((stat.avg_latency as number | undefined) ?? 0).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
