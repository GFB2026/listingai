"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { ContentItem } from "@/hooks/useContent";

export default function DashboardPage() {
  const { user } = useAuth();

  const { data: usage } = useQuery({
    queryKey: ["billing", "usage"],
    queryFn: async () => {
      const res = await api.get("/billing/usage");
      return res.data;
    },
  });

  const { data: recentContent } = useQuery({
    queryKey: ["content", "recent"],
    queryFn: async () => {
      const res = await api.get("/content", { params: { page_size: 5 } });
      return res.data;
    },
  });

  const { data: listings } = useQuery({
    queryKey: ["listings", "count"],
    queryFn: async () => {
      const res = await api.get("/listings", { params: { page_size: 1 } });
      return res.data;
    },
  });

  const { data: leadsData } = useQuery({
    queryKey: ["leads", "count"],
    queryFn: async () => {
      const res = await api.get("/leads", { params: { page_size: 1 } });
      return res.data;
    },
  });

  const { data: newLeadsData } = useQuery({
    queryKey: ["leads", "new-count"],
    queryFn: async () => {
      const res = await api.get("/leads", {
        params: { pipeline_status: "new", page_size: 1 },
      });
      return res.data;
    },
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        Welcome back, {user?.full_name?.split(" ")[0] || "there"}
      </h1>

      {/* Stats Cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Generations This Month"
          value={usage?.credits_used ?? "—"}
          sub={`of ${usage?.credits_limit ?? "—"} limit`}
        />
        <StatCard
          label="Credits Remaining"
          value={usage?.credits_remaining ?? "—"}
          sub={usage?.plan ?? "free"}
        />
        <StatCard
          label="Active Listings"
          value={listings?.total ?? "—"}
          sub="synced from MLS"
        />
        <StatCard
          label="Content Created"
          value={recentContent?.total ?? "—"}
          sub="all time"
        />
        <StatCard
          label="Total Leads"
          value={leadsData?.total ?? "—"}
          sub="all time"
        />
        <StatCard
          label="New Leads"
          value={newLeadsData?.total ?? "—"}
          sub="awaiting contact"
        />
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Quick Actions
        </h2>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/listings"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light"
          >
            Browse Listings
          </Link>
          <Link
            href="/content"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Content Library
          </Link>
          <Link
            href="/leads"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Lead Pipeline
          </Link>
          <Link
            href="/brand"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Brand Profiles
          </Link>
        </div>
      </div>

      {/* Recent Content */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Recent Content
        </h2>
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          {recentContent?.content?.length ? (
            <ul className="divide-y divide-gray-100">
              {recentContent.content.map((item: ContentItem) => (
                <li key={item.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <span className="text-sm font-medium text-gray-900">
                      {item.content_type.replace(/_/g, " ")}
                    </span>
                    <span className="ml-2 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {item.tone}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-8 text-center text-sm text-gray-400">
              No content generated yet. Start by selecting a listing.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400">{sub}</p>
    </div>
  );
}
