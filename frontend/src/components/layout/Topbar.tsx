"use client";

import { useAuth } from "@/lib/auth";
import { useAppStore } from "@/stores/app-store";

export function Topbar() {
  const { user, logout } = useAuth();
  const { toggleSidebar } = useAppStore();

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Redirect to login even if logout API fails
      window.location.href = "/login";
    }
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-6">
      <button
        onClick={toggleSidebar}
        className="text-gray-500 hover:text-gray-700"
        aria-label="Toggle sidebar"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">{user?.full_name}</span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
