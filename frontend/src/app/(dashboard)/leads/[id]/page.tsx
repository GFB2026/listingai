"use client";

import { use } from "react";
import Link from "next/link";
import { LeadDetailPanel } from "@/components/leads/LeadDetailPanel";

export default function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/leads"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          &larr; Back to Pipeline
        </Link>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <LeadDetailPanel
          leadId={id}
          onClose={() => {
            window.history.back();
          }}
        />
      </div>
    </div>
  );
}
