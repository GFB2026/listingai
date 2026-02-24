"use client";

import { cn, formatDate, truncate } from "@/lib/utils";

interface LeadCardLead {
  id: string;
  first_name: string;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  property_interest: string | null;
  utm_source: string | null;
  created_at: string;
  agent_name: string | null;
}

interface LeadCardProps {
  lead: LeadCardLead;
  onClick: (id: string) => void;
}

const SOURCE_BADGES: Record<string, { label: string; className: string }> = {
  facebook: { label: "FB", className: "bg-blue-100 text-blue-700" },
  instagram: { label: "IG", className: "bg-pink-100 text-pink-700" },
  google: { label: "G", className: "bg-red-100 text-red-700" },
  tiktok: { label: "TT", className: "bg-gray-900 text-white" },
  linkedin: { label: "LI", className: "bg-blue-200 text-blue-800" },
  twitter: { label: "X", className: "bg-gray-100 text-gray-800" },
  email: { label: "EM", className: "bg-yellow-100 text-yellow-700" },
  referral: { label: "REF", className: "bg-green-100 text-green-700" },
  direct: { label: "DIR", className: "bg-gray-100 text-gray-600" },
};

function getSourceBadge(source: string | null) {
  if (!source) return null;
  const key = source.toLowerCase();
  return SOURCE_BADGES[key] || { label: source.slice(0, 3).toUpperCase(), className: "bg-gray-100 text-gray-600" };
}

export function LeadCard({ lead, onClick }: LeadCardProps) {
  const fullName = [lead.first_name, lead.last_name].filter(Boolean).join(" ");
  const sourceBadge = getSourceBadge(lead.utm_source);

  return (
    <button
      type="button"
      onClick={() => onClick(lead.id)}
      className={cn(
        "w-full rounded-lg border border-gray-200 bg-white p-3 text-left transition-shadow",
        "hover:shadow-md hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary/20"
      )}
    >
      <div className="mb-1.5 flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-gray-900 leading-tight">
          {fullName}
        </span>
        {sourceBadge && (
          <span
            className={cn(
              "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold",
              sourceBadge.className
            )}
          >
            {sourceBadge.label}
          </span>
        )}
      </div>

      {(lead.email || lead.phone) && (
        <p className="mb-1 text-xs text-gray-500 truncate">
          {lead.email || lead.phone}
        </p>
      )}

      {lead.property_interest && (
        <p className="mb-1.5 text-xs text-gray-600 leading-snug">
          {truncate(lead.property_interest, 60)}
        </p>
      )}

      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span>{formatDate(lead.created_at)}</span>
        {lead.agent_name && (
          <span className="truncate ml-2">{lead.agent_name}</span>
        )}
      </div>
    </button>
  );
}
