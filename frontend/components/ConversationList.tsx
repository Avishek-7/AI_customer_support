import { useState } from "react";

type Conversation = {
  id: number;
  title: string;
  created_at: string;
};

type ConversationListProps = {
  conversations: Conversation[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onRename: (id: number, title: string) => void;
  onDelete: (id: number) => void;
  onCreateNew: () => void;
  loading?: boolean;
};

export default function ConversationList({
  conversations,
  activeId,
  onSelect,
  onRename,
  onDelete,
  onCreateNew,
  loading = false,
}: ConversationListProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const handleStartEdit = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveEdit = (id: number) => {
    if (editTitle.trim()) {
      onRename(id, editTitle);
      setEditingId(null);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-800 border-r border-gray-700">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={onCreateNew}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-2 px-4 rounded transition"
        >
          + New Conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-gray-400 text-center text-sm">
            No conversations yet. Start a new one!
          </div>
        ) : (
          <div className="space-y-2 p-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`relative group ${
                  activeId === conv.id ? "bg-gray-700" : "bg-gray-800 hover:bg-gray-700"
                } rounded p-3 cursor-pointer transition`}
              >
                {editingId === conv.id ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      autoFocus
                      className="flex-1 bg-gray-600 text-white px-2 py-1 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => handleSaveEdit(conv.id)}
                      className="bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded text-sm font-semibold"
                    >
                      ✓
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded text-sm font-semibold"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between" onClick={() => onSelect(conv.id)}>
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-medium truncate">{conv.title}</p>
                      <p className="text-gray-400 text-xs mt-1">
                        {new Date(conv.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartEdit(conv);
                        }}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded text-xs font-semibold"
                        title="Rename"
                      >
                        ✎
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Delete "${conv.title}"? This cannot be undone.`)) {
                            onDelete(conv.id);
                          }
                        }}
                        className="bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded text-xs font-semibold"
                        title="Delete"
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
