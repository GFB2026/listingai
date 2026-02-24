import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

export interface Lead {
  id: string;
  tenant_id: string;
  agent_page_id: string | null;
  agent_id: string | null;
  listing_id: string | null;
  first_name: string;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  message: string | null;
  property_interest: string | null;
  pipeline_status: string;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_content: string | null;
  utm_term: string | null;
  referrer_url: string | null;
  landing_url: string | null;
  closed_value: number | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string | null;
  agent_name: string | null;
}

export interface Activity {
  id: string;
  lead_id: string;
  user_id: string;
  activity_type: string;
  old_value: string | null;
  new_value: string | null;
  note: string | null;
  created_at: string;
  user_name: string | null;
}

interface LeadListResponse {
  leads: Lead[];
  total: number;
  page: number;
  page_size: number;
}

interface LeadDetailResponse {
  lead: Lead;
  activities: Activity[];
}

interface LeadFilters {
  pipeline_status?: string;
  utm_source?: string;
  agent_id?: string;
  page?: number;
  page_size?: number;
}

interface LeadUpdateData {
  id: string;
  pipeline_status?: string;
  closed_value?: number | null;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  property_interest?: string;
}

interface ActivityCreateData {
  leadId: string;
  activity_type: string;
  note?: string;
}

export function useLeads(filters: LeadFilters = {}) {
  return useQuery<LeadListResponse>({
    queryKey: ["leads", filters],
    queryFn: async ({ signal }) => {
      const params: Record<string, string | number> = {
        page: filters.page || 1,
        page_size: filters.page_size || 50,
      };
      if (filters.pipeline_status) params.pipeline_status = filters.pipeline_status;
      if (filters.utm_source) params.utm_source = filters.utm_source;
      if (filters.agent_id) params.agent_id = filters.agent_id;

      const res = await api.get("/leads", { params, signal });
      return res.data;
    },
  });
}

export function useLead(id: string) {
  return useQuery<LeadDetailResponse>({
    queryKey: ["lead", id],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/leads/${id}`, { signal });
      return res.data;
    },
    enabled: !!id,
  });
}

export function useUpdateLead() {
  const queryClient = useQueryClient();

  return useMutation<Lead, Error, LeadUpdateData>({
    mutationFn: async ({ id, ...data }) => {
      const res = await api.patch(`/leads/${id}`, data);
      return res.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["lead", variables.id] });
      useToastStore.getState().toast({
        title: "Lead updated",
        description: "Lead has been updated successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Update failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}

export function useDeleteLead() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/leads/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      useToastStore.getState().toast({
        title: "Lead deleted",
        description: "Lead has been deleted successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Delete failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}

export function useAddActivity() {
  const queryClient = useQueryClient();

  return useMutation<Activity, Error, ActivityCreateData>({
    mutationFn: async ({ leadId, ...data }) => {
      const res = await api.post(`/leads/${leadId}/activities`, data);
      return res.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["lead", variables.leadId] });
      useToastStore.getState().toast({
        title: "Activity added",
        description: "Activity has been recorded.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Failed to add activity",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}
