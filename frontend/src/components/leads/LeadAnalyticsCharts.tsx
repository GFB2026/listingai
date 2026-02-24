"use client";

import { cn, formatPrice } from "@/lib/utils";

interface SummaryData {
  total_leads: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  by_agent: Array<{ agent_name: string; agent_id: string; count: number }>;
  total_closed_value: number;
}

interface FunnelStep {
  status: string;
  count: number;
  percentage: number;
}

interface FunnelData {
  funnel: FunnelStep[];
  total: number;
}

interface LeadAnalyticsChartsProps {
  summary: SummaryData;
  funnel: FunnelData;
}

const SOURCE_COLORS: Record<string, string> = {
  facebook: "bg-blue-500",
  instagram: "bg-pink-500",
  google: "bg-red-500",
  tiktok: "bg-gray-800",
  linkedin: "bg-blue-700",
  twitter: "bg-sky-500",
  email: "bg-yellow-500",
  referral: "bg-green-500",
  direct: "bg-gray-400",
};

const FUNNEL_COLORS: Record<string, string> = {
  new: "bg-blue-500",
  contacted: "bg-orange-500",
  showing: "bg-purple-500",
  under_contract: "bg-cyan-500",
  closed: "bg-green-500",
  lost: "bg-gray-400",
};

function formatStatusLabel(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getSourceColor(source: string): string {
  return SOURCE_COLORS[source.toLowerCase()] || "bg-gray-400";
}

export function LeadAnalyticsCharts({ summary, funnel }: LeadAnalyticsChartsProps) {
  const sourceEntries = Object.entries(summary.by_source).sort(([, a], [, b]) => b - a);
  const maxSourceCount = sourceEntries.length > 0 ? sourceEntries[0][1] : 1;

  return (
    <div className="space-y-6">
      {/* Total Closed Revenue */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-2 text-sm font-medium text-gray-500">Total Closed Revenue</h3>
        <p className="text-4xl font-bold text-green-600">
          {formatPrice(summary.total_closed_value)}
        </p>
        <p className="mt-1 text-xs text-gray-400">
          From {summary.by_status["closed"] ?? 0} closed deals
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Leads by Source - Horizontal bar chart */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-800">Leads by Source</h3>
          {sourceEntries.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">No source data</p>
          ) : (
            <div className="space-y-3">
              {sourceEntries.map(([source, count]) => {
                const percentage = Math.round((count / summary.total_leads) * 100);
                const barWidth = Math.max((count / maxSourceCount) * 100, 4);

                return (
                  <div key={source}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium text-gray-700 capitalize">{source}</span>
                      <span className="text-gray-500">
                        {count} ({percentage}%)
                      </span>
                    </div>
                    <div className="h-3 w-full overflow-hidden rounded-full bg-gray-100">
                      <div
                        className={cn("h-full rounded-full transition-all", getSourceColor(source))}
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Pipeline Funnel */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-800">Pipeline Funnel</h3>
          {funnel.funnel.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">No funnel data</p>
          ) : (
            <div className="space-y-2">
              {funnel.funnel.map((step) => {
                const barWidth = Math.max(step.percentage, 4);
                const barColor = FUNNEL_COLORS[step.status] || "bg-gray-400";

                return (
                  <div key={step.status} className="flex items-center gap-3">
                    <span className="w-28 shrink-0 text-right text-xs font-medium text-gray-600">
                      {formatStatusLabel(step.status)}
                    </span>
                    <div className="flex-1">
                      <div className="h-7 w-full overflow-hidden rounded bg-gray-50">
                        <div
                          className={cn(
                            "flex h-full items-center rounded px-2 text-[10px] font-bold text-white transition-all",
                            barColor
                          )}
                          style={{ width: `${barWidth}%` }}
                        >
                          {step.count > 0 && step.count}
                        </div>
                      </div>
                    </div>
                    <span className="w-10 shrink-0 text-right text-xs text-gray-400">
                      {Math.round(step.percentage)}%
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Agent Leaderboard */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-800">Agent Leaderboard</h3>
        {summary.by_agent.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-400">No agent data</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {summary.by_agent
              .sort((a, b) => b.count - a.count)
              .map((agent, index) => (
                <div
                  key={agent.agent_id}
                  className="flex items-center justify-between py-3"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold",
                        index === 0
                          ? "bg-yellow-100 text-yellow-700"
                          : index === 1
                            ? "bg-gray-200 text-gray-600"
                            : index === 2
                              ? "bg-orange-100 text-orange-600"
                              : "bg-gray-100 text-gray-500"
                      )}
                    >
                      {index + 1}
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {agent.agent_name}
                    </span>
                  </div>
                  <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-700">
                    {agent.count} {agent.count === 1 ? "lead" : "leads"}
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
