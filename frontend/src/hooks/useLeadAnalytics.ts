import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export interface LeadSummary {
  total_leads: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  by_agent: Array<{ agent_name: string; agent_id: string; count: number }>;
  total_closed_value: number;
}

export interface FunnelStep {
  status: string;
  count: number;
  percentage: number;
}

export interface LeadFunnel {
  funnel: FunnelStep[];
  total: number;
}

export function useLeadSummary() {
  return useQuery<LeadSummary>({
    queryKey: ["leads", "analytics", "summary"],
    queryFn: async ({ signal }) => {
      const res = await api.get("/leads/analytics/summary", { signal });
      return res.data;
    },
  });
}

export function useLeadFunnel() {
  return useQuery<LeadFunnel>({
    queryKey: ["leads", "analytics", "funnel"],
    queryFn: async ({ signal }) => {
      const res = await api.get("/leads/analytics/funnel", { signal });
      return res.data;
    },
  });
}
