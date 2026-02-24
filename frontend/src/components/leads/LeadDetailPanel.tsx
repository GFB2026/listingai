"use client";

import { useState, useEffect } from "react";
import { cn, formatDate, formatPrice } from "@/lib/utils";
import { useLead, useUpdateLead } from "@/hooks/useLeads";
import { ActivityTimeline } from "./ActivityTimeline";

interface LeadDetailPanelProps {
  leadId: string;
  onClose: () => void;
}

const PIPELINE_STATUSES = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "showing", label: "Showing" },
  { value: "under_contract", label: "Under Contract" },
  { value: "closed", label: "Closed" },
  { value: "lost", label: "Lost" },
] as const;

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  contacted: "bg-orange-100 text-orange-700",
  showing: "bg-purple-100 text-purple-700",
  under_contract: "bg-cyan-100 text-cyan-700",
  closed: "bg-green-100 text-green-700",
  lost: "bg-gray-100 text-gray-600",
};

export function LeadDetailPanel({ leadId, onClose }: LeadDetailPanelProps) {
  const { data, isLoading } = useLead(leadId);
  const updateLead = useUpdateLead();

  const [status, setStatus] = useState("");
  const [closedValue, setClosedValue] = useState("");

  const lead = data?.lead;
  const activities = data?.activities ?? [];

  useEffect(() => {
    if (lead) {
      setStatus(lead.pipeline_status);
      setClosedValue(lead.closed_value != null ? String(lead.closed_value) : "");
    }
  }, [lead]);

  const handleStatusChange = (newStatus: string) => {
    setStatus(newStatus);
    const updateData: { id: string; pipeline_status: string; closed_value?: number | null } = {
      id: leadId,
      pipeline_status: newStatus,
    };
    // If moving away from closed, clear closed value
    if (newStatus !== "closed") {
      updateData.closed_value = null;
    }
    updateLead.mutate(updateData);
  };

  const handleClosedValueSave = () => {
    const numValue = closedValue ? parseFloat(closedValue) : null;
    if (numValue !== lead?.closed_value) {
      updateLead.mutate({ id: leadId, closed_value: numValue });
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-400">Loading lead details...</p>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-400">Lead not found</p>
      </div>
    );
  }

  const fullName = [lead.first_name, lead.last_name].filter(Boolean).join(" ");

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-gray-200 px-6 py-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">{fullName}</h2>
          <p className="mt-0.5 text-xs text-gray-400">
            Created {formatDate(lead.created_at)}
            {lead.agent_name && <span> &middot; Agent: {lead.agent_name}</span>}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close"
        >
          <span className="text-lg leading-none">&times;</span>
        </button>
      </div>

      <div className="flex-1 space-y-6 p-6">
        {/* Pipeline Status */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700">
            Pipeline Status
          </label>
          <div className="flex flex-wrap gap-2">
            {PIPELINE_STATUSES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => handleStatusChange(s.value)}
                disabled={updateLead.isPending}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                  status === s.value
                    ? STATUS_COLORS[s.value]
                    : "border border-gray-200 bg-white text-gray-500 hover:bg-gray-50"
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Closed Value - visible when status is "closed" */}
        {status === "closed" && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-700">
              Closed Value
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                value={closedValue}
                onChange={(e) => setClosedValue(e.target.value)}
                placeholder="Enter deal value"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
              <button
                type="button"
                onClick={handleClosedValueSave}
                disabled={updateLead.isPending}
                className="shrink-0 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
              >
                Save
              </button>
            </div>
            {lead.closed_value != null && (
              <p className="mt-1 text-xs text-gray-400">
                Current: {formatPrice(lead.closed_value)}
              </p>
            )}
          </div>
        )}

        {/* Contact Info */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-800">Contact Information</h3>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-gray-500">Name</dt>
              <dd className="font-medium text-gray-900">{fullName}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Email</dt>
              <dd className="font-medium text-gray-900">
                {lead.email ? (
                  <a href={`mailto:${lead.email}`} className="text-primary hover:underline">
                    {lead.email}
                  </a>
                ) : (
                  "---"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Phone</dt>
              <dd className="font-medium text-gray-900">
                {lead.phone ? (
                  <a href={`tel:${lead.phone}`} className="text-primary hover:underline">
                    {lead.phone}
                  </a>
                ) : (
                  "---"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Property Interest</dt>
              <dd className="font-medium text-gray-900">{lead.property_interest || "---"}</dd>
            </div>
          </dl>
          {lead.message && (
            <div className="mt-3 border-t border-gray-100 pt-3">
              <dt className="text-xs text-gray-500">Message</dt>
              <dd className="mt-1 text-sm text-gray-700 leading-relaxed">{lead.message}</dd>
            </div>
          )}
        </div>

        {/* UTM Attribution */}
        {(lead.utm_source || lead.utm_medium || lead.utm_campaign || lead.referrer_url) && (
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="mb-3 text-sm font-semibold text-gray-800">Attribution</h3>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {lead.utm_source && (
                <div>
                  <dt className="text-gray-500">Source</dt>
                  <dd className="font-medium text-gray-900">{lead.utm_source}</dd>
                </div>
              )}
              {lead.utm_medium && (
                <div>
                  <dt className="text-gray-500">Medium</dt>
                  <dd className="font-medium text-gray-900">{lead.utm_medium}</dd>
                </div>
              )}
              {lead.utm_campaign && (
                <div>
                  <dt className="text-gray-500">Campaign</dt>
                  <dd className="font-medium text-gray-900">{lead.utm_campaign}</dd>
                </div>
              )}
              {lead.utm_content && (
                <div>
                  <dt className="text-gray-500">Content</dt>
                  <dd className="font-medium text-gray-900">{lead.utm_content}</dd>
                </div>
              )}
              {lead.utm_term && (
                <div>
                  <dt className="text-gray-500">Term</dt>
                  <dd className="font-medium text-gray-900">{lead.utm_term}</dd>
                </div>
              )}
              {lead.referrer_url && (
                <div className="col-span-2">
                  <dt className="text-gray-500">Referrer</dt>
                  <dd className="font-medium text-gray-900 truncate">{lead.referrer_url}</dd>
                </div>
              )}
              {lead.landing_url && (
                <div className="col-span-2">
                  <dt className="text-gray-500">Landing Page</dt>
                  <dd className="font-medium text-gray-900 truncate">{lead.landing_url}</dd>
                </div>
              )}
            </dl>
          </div>
        )}

        {/* Activity Timeline */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="mb-4 text-sm font-semibold text-gray-800">Activity</h3>
          <ActivityTimeline activities={activities} leadId={leadId} />
        </div>
      </div>
    </div>
  );
}
