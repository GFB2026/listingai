"use client";

import { useAuth } from "@/lib/auth";
import { useLeadSummary, useLeadFunnel } from "@/hooks/useLeadAnalytics";
import { LeadAnalyticsCharts } from "@/components/leads/LeadAnalyticsCharts";
import { formatPrice } from "@/lib/utils";

export default function LeadAnalyticsPage() {
  const { user } = useAuth();

  // Role check: only broker/admin
  if (user?.role === "agent") {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="rounded-lg border border-red-200 bg-red-50 px-8 py-6 text-center">
          <h2 className="text-lg font-semibold text-red-800">Access Denied</h2>
          <p className="mt-1 text-sm text-red-600">
            Lead analytics are only available to brokers and administrators.
          </p>
        </div>
      </div>
    );
  }

  const { data: summary, isLoading: summaryLoading } = useLeadSummary();
  const { data: funnel, isLoading: funnelLoading } = useLeadFunnel();

  const isLoading = summaryLoading || funnelLoading;

  if (isLoading) {
    return (
      <div className="py-12 text-center text-gray-400">Loading analytics...</div>
    );
  }

  if (!summary || !funnel) {
    return (
      <div className="py-12 text-center text-gray-400">
        Unable to load analytics data.
      </div>
    );
  }

  // Calculate conversion rate: closed / total
  const closedCount = summary.by_status["closed"] ?? 0;
  const conversionRate =
    summary.total_leads > 0
      ? ((closedCount / summary.total_leads) * 100).toFixed(1)
      : "0.0";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Lead Analytics</h1>
        <p className="text-sm text-gray-500">
          Overview of your lead pipeline performance
        </p>
      </div>

      {/* Stat cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-sm text-gray-500">Total Leads</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{summary.total_leads}</p>
          <p className="text-xs text-gray-400">all time</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-sm text-gray-500">Closed Deals</p>
          <p className="mt-1 text-2xl font-bold text-green-600">{closedCount}</p>
          <p className="text-xs text-gray-400">total closed</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-sm text-gray-500">Conversion Rate</p>
          <p className="mt-1 text-2xl font-bold text-primary">{conversionRate}%</p>
          <p className="text-xs text-gray-400">leads to closed</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-sm text-gray-500">Total Revenue</p>
          <p className="mt-1 text-2xl font-bold text-green-600">
            {formatPrice(summary.total_closed_value)}
          </p>
          <p className="text-xs text-gray-400">closed deal value</p>
        </div>
      </div>

      {/* Charts */}
      <LeadAnalyticsCharts summary={summary} funnel={funnel} />
    </div>
  );
}
