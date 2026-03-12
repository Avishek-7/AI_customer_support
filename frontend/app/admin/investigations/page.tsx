"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import {
  InvestigationIntent,
  AdminInvestigationRunResponse,
  runAdminInvestigation,
} from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

const INTENT_OPTIONS: Array<{ value: InvestigationIntent; label: string }> = [
  { value: "investigate_root_cause", label: "Investigate Root Cause" },
  { value: "explain_low_confidence", label: "Explain Low Confidence" },
  { value: "draft_improved_answer", label: "Draft Improved Answer" },
  { value: "recommend_next_action", label: "Recommend Next Action" },
];

function formatPct(value: number | null | undefined): string {
  if (typeof value !== "number") {
    return "N/A";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export default function AdminInvestigationsPage() {
  const router = useRouter();
  const [conversationId, setConversationId] = useState("");
  const [intent, setIntent] = useState<InvestigationIntent>("investigate_root_cause");
  const [constraints, setConstraints] = useState("");
  const [k, setK] = useState("5");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdminInvestigationRunResponse | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();

    const token = getStoredToken();
    if (!token) {
      router.push("/login");
      return;
    }

    const parsedConversationId = Number.parseInt(conversationId, 10);
    if (!Number.isInteger(parsedConversationId) || Number.isNaN(parsedConversationId) || parsedConversationId <= 0) {
      setError("Please enter a valid conversation ID");
      return;
    }

    const parsedK = Number.parseInt(k, 10);
    if (!Number.isInteger(parsedK) || Number.isNaN(parsedK) || parsedK <= 0 || parsedK > 20) {
      setError("k must be an integer between 1 and 20");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = await runAdminInvestigation(
        {
          conversation_id: parsedConversationId,
          instruction_intent: intent,
          constraints: constraints.trim() || undefined,
          k: parsedK,
        },
        token,
      );
      setResult(payload);
    } catch (err) {
      setError(`Investigation failed: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/admin" className="text-blue-400 hover:text-blue-300 text-sm mb-4 inline-block">
          ← Back to Admin
        </Link>
        <h1 className="text-4xl font-bold mb-2">Conversation Investigator</h1>
        <p className="text-gray-300 mb-8">Admin-only, read-only investigation workflow for weak or risky responses.</p>

        <form onSubmit={onSubmit} className="bg-gray-800 p-6 rounded-lg mb-8 space-y-4">
          <div>
            <label htmlFor="conversation-id" className="block text-sm font-semibold mb-2">Conversation ID</label>
            <input
              id="conversation-id"
              type="number"
              value={conversationId}
              onChange={(e) => setConversationId(e.target.value)}
              placeholder="Enter conversation ID"
              className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
            />
          </div>

          <div>
            <label htmlFor="intent" className="block text-sm font-semibold mb-2">Instruction Intent</label>
            <select
              id="intent"
              value={intent}
              onChange={(e) => setIntent(e.target.value as InvestigationIntent)}
              className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white"
            >
              {INTENT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="constraints" className="block text-sm font-semibold mb-2">Optional Regeneration Constraints</label>
            <textarea
              id="constraints"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              rows={3}
              placeholder="Example: make it shorter and focus on policy grounding"
              className="w-full px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white placeholder-gray-400"
            />
          </div>

          <div>
            <label htmlFor="k" className="block text-sm font-semibold mb-2">Retrieval Depth (k)</label>
            <input
              id="k"
              type="number"
              value={k}
              onChange={(e) => setK(e.target.value)}
              className="w-40 px-3 py-2 rounded bg-gray-700 border border-gray-600 text-white"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 rounded bg-blue-600 hover:bg-blue-700 disabled:opacity-50 font-semibold"
          >
            {loading ? "Running..." : "Run Investigation"}
          </button>
        </form>

        {result ? (
          <div className="space-y-6">
            <div className="bg-gray-800 p-6 rounded-lg">
              <h2 className="text-2xl font-bold mb-2">Investigation Result</h2>
              <p className="text-gray-400 text-sm">Investigation #{result.investigation_id} • {result.status}</p>
              <p className="mt-3 text-white">{result.diagnosis}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-800 p-4 rounded">
                <p className="text-gray-400 text-sm">Confidence</p>
                <p className="text-2xl font-bold text-green-400">{formatPct(result.quality_summary.confidence_score)}</p>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <p className="text-gray-400 text-sm">Hallucination</p>
                <p className="text-2xl font-bold text-orange-400">{formatPct(result.quality_summary.hallucination_score)}</p>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <p className="text-gray-400 text-sm">Alignment</p>
                <p className="text-2xl font-bold text-blue-400">{formatPct(result.quality_summary.alignment_score)}</p>
              </div>
            </div>

            <div className="bg-gray-800 p-6 rounded-lg">
              <h3 className="text-xl font-bold mb-3">Recommended Next Actions</h3>
              <ul className="list-disc pl-5 space-y-1 text-gray-200">
                {result.recommended_next_actions.map((item, idx) => (
                  <li key={`${item}-${idx}`}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-800 p-6 rounded-lg">
              <h3 className="text-xl font-bold mb-3">Evidence</h3>
              <p className="text-gray-300 text-sm mb-2">
                Retrieved chunks: {result.supporting_evidence.total_chunks_retrieved} • Document IDs: {result.supporting_evidence.document_ids.join(", ") || "None"}
              </p>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {result.supporting_evidence.retrieved_chunks.map((chunk, idx) => (
                  <div key={idx} className="bg-gray-700 p-3 rounded text-sm">
                    <p className="text-gray-400">Chunk {idx + 1}</p>
                    <p className="mt-1 whitespace-pre-wrap text-gray-100">{String(chunk.text_preview ?? chunk.text ?? "")}</p>
                  </div>
                ))}
              </div>
            </div>

            {result.improved_draft_answer ? (
              <div className="bg-gray-800 p-6 rounded-lg">
                <h3 className="text-xl font-bold mb-3">Improved Draft Answer</h3>
                <p className="whitespace-pre-wrap text-gray-100">{result.improved_draft_answer}</p>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
