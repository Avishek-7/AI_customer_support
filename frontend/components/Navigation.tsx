import Link from "next/link";

export default function Navigation() {
  return (
    <nav className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
      <Link href="/chat" className="text-xl font-bold text-blue-400 hover:text-blue-300">
        AI Customer Support
      </Link>
      
      <div className="flex gap-4 items-center">
        <Link href="/profile" className="hover:text-blue-300 transition">
          👤 Profile
        </Link>
        <Link href="/documents" className="hover:text-blue-300 transition">
          📄 Documents
        </Link>
        <Link href="/admin" className="hover:text-blue-300 transition">
          ⚙️ Admin
        </Link>
        <button
          onClick={() => {
            localStorage.removeItem("token");
            window.location.href = "/login";
          }}
          className="px-3 py-1 rounded bg-red-600 hover:bg-red-700 text-sm font-semibold"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
