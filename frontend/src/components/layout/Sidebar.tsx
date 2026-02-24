"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/stores/app-store";

const navItems = [
  { href: "/", label: "Dashboard", icon: "H" },
  { href: "/listings", label: "Listings", icon: "L" },
  { href: "/content", label: "Content", icon: "C" },
  { href: "/leads", label: "Leads", icon: "T" },
  { href: "/leads/analytics", label: "Analytics", icon: "A" },
  { href: "/brand", label: "Brand", icon: "B" },
  { href: "/settings", label: "Settings", icon: "S" },
  { href: "/settings/mls", label: "MLS", icon: "M" },
  { href: "/settings/agent-pages", label: "Agent Pages", icon: "P" },
  { href: "/billing", label: "Billing", icon: "$" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen } = useAppStore();

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-gray-200 bg-white transition-all",
        sidebarOpen ? "w-56" : "w-16"
      )}
    >
      <div className="flex h-14 items-center border-b border-gray-200 px-4">
        <Link href="/" className="text-lg font-bold text-primary">
          {sidebarOpen ? "ListingAI" : "LA"}
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href ||
                (pathname.startsWith(item.href + "/") &&
                  !navItems.some(
                    (other) =>
                      other.href !== item.href &&
                      other.href.startsWith(item.href + "/") &&
                      pathname.startsWith(other.href)
                  ));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <span className="flex h-6 w-6 items-center justify-center rounded text-xs font-bold">
                {item.icon}
              </span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
