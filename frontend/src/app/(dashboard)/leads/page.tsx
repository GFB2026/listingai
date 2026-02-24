"use client";

import { useState, useCallback } from "react";
import { useLeads, useUpdateLead } from "@/hooks/useLeads";
import { LeadPipelineBoard } from "@/components/leads/LeadPipelineBoard";
import { LeadDetailPanel } from "@/components/leads/LeadDetailPanel";

export default function LeadsPage() {
  const [filters, setFilters] = useState({
    pipeline_status: "",
    utm_source: "",
    agent_id: "",
  });
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  const { data, isLoading } = useLeads({
    ...filters,
    page_size: 200, // Load all leads for kanban view
  });
  const updateLead = useUpdateLead();

  const handleStatusChange = useCallback(
    (leadId: string, newStatus: string) => {
      updateLead.mutate({ id: leadId, pipeline_status: newStatus });
    },
    [updateLead]
  );

  const handleLeadClick = useCallback((leadId: string) => {
    setSelectedLeadId(leadId);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedLeadId(null);
  }, []);

  return (
    <div className="relative">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Lead Pipeline</h1>
        <p className="text-sm text-gray-500">
          {data?.total ?? 0} total leads
        </p>
      </div>

      {/* Filter bar */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          value={filters.pipeline_status}
          onChange={(e) => setFilters((f) => ({ ...f, pipeline_status: e.target.value }))}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        >
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="showing">Showing</option>
          <option value="under_contract">Under Contract</option>
          <option value="closed">Closed</option>
          <option value="lost">Lost</option>
        </select>

        <select
          value={filters.utm_source}
          onChange={(e) => setFilters((f) => ({ ...f, utm_source: e.target.value }))}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        >
          <option value="">All Sources</option>
          <option value="facebook">Facebook</option>
          <option value="instagram">Instagram</option>
          <option value="google">Google</option>
          <option value="tiktok">TikTok</option>
          <option value="linkedin">LinkedIn</option>
          <option value="email">Email</option>
          <option value="referral">Referral</option>
          <option value="direct">Direct</option>
        </select>

        <input
          type="text"
          value={filters.agent_id}
          onChange={(e) => setFilters((f) => ({ ...f, agent_id: e.target.value }))}
          placeholder="Filter by agent ID..."
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        />

        {(filters.pipeline_status || filters.utm_source || filters.agent_id) && (
          <button
            onClick={() => setFilters({ pipeline_status: "", utm_source: "", agent_id: "" })}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-500 hover:bg-gray-50"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Pipeline board */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400">Loading leads...</div>
      ) : (
        <LeadPipelineBoard
          leads={data?.leads ?? []}
          onStatusChange={handleStatusChange}
          onLeadClick={handleLeadClick}
        />
      )}

      {/* Detail slide-over */}
      {selectedLeadId && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={handleCloseDetail}
          />

          {/* Panel */}
          <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg border-l border-gray-200 bg-white shadow-xl">
            <LeadDetailPanel leadId={selectedLeadId} onClose={handleCloseDetail} />
          </div>
        </>
      )}
    </div>
  );
}
