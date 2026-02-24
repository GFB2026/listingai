"use client";

import { cn } from "@/lib/utils";
import { LeadCard } from "./LeadCard";

interface PipelineLead {
  id: string;
  first_name: string;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  property_interest: string | null;
  pipeline_status: string;
  utm_source: string | null;
  created_at: string;
  agent_name: string | null;
}

interface LeadPipelineBoardProps {
  leads: PipelineLead[];
  onStatusChange: (leadId: string, newStatus: string) => void;
  onLeadClick: (leadId: string) => void;
}

const PIPELINE_COLUMNS = [
  { status: "new", label: "New", color: "bg-blue-500", headerBg: "bg-blue-50", headerText: "text-blue-700" },
  { status: "contacted", label: "Contacted", color: "bg-orange-500", headerBg: "bg-orange-50", headerText: "text-orange-700" },
  { status: "showing", label: "Showing", color: "bg-purple-500", headerBg: "bg-purple-50", headerText: "text-purple-700" },
  { status: "under_contract", label: "Under Contract", color: "bg-cyan-500", headerBg: "bg-cyan-50", headerText: "text-cyan-700" },
  { status: "closed", label: "Closed", color: "bg-green-500", headerBg: "bg-green-50", headerText: "text-green-700" },
  { status: "lost", label: "Lost", color: "bg-gray-400", headerBg: "bg-gray-50", headerText: "text-gray-600" },
] as const;

export function LeadPipelineBoard({ leads, onStatusChange, onLeadClick }: LeadPipelineBoardProps) {
  const leadsByStatus = PIPELINE_COLUMNS.map((col) => ({
    ...col,
    leads: leads.filter((l) => l.pipeline_status === col.status),
  }));

  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {leadsByStatus.map((column) => (
        <div
          key={column.status}
          className="flex w-64 shrink-0 flex-col rounded-lg border border-gray-200 bg-gray-50 lg:w-auto lg:min-w-[220px] lg:flex-1"
        >
          {/* Column header */}
          <div className={cn("flex items-center justify-between rounded-t-lg px-3 py-2.5", column.headerBg)}>
            <div className="flex items-center gap-2">
              <div className={cn("h-2.5 w-2.5 rounded-full", column.color)} />
              <span className={cn("text-sm font-semibold", column.headerText)}>
                {column.label}
              </span>
            </div>
            <span
              className={cn(
                "flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[10px] font-bold",
                column.headerBg,
                column.headerText
              )}
            >
              {column.leads.length}
            </span>
          </div>

          {/* Cards */}
          <div className="flex flex-1 flex-col gap-2 p-2 overflow-y-auto max-h-[calc(100vh-280px)]">
            {column.leads.length === 0 ? (
              <p className="py-8 text-center text-xs text-gray-400">No leads</p>
            ) : (
              column.leads.map((lead) => (
                <div key={lead.id} className="group relative">
                  <LeadCard lead={lead} onClick={onLeadClick} />

                  {/* Quick status change dropdown */}
                  <div className="absolute right-1 top-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <select
                      value={lead.pipeline_status}
                      onChange={(e) => {
                        e.stopPropagation();
                        if (e.target.value !== lead.pipeline_status) {
                          onStatusChange(lead.id, e.target.value);
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border border-gray-300 bg-white px-1 py-0.5 text-[10px] text-gray-600 shadow-sm cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary/30"
                    >
                      {PIPELINE_COLUMNS.map((col) => (
                        <option key={col.status} value={col.status}>
                          {col.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
