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

export interface EmailSendRequest {
  to_emails: string[];
  subject: string;
  html_content: string;
  campaign_type?: string;
  reply_to?: string;
  content_id?: string;
  listing_id?: string;
}

export interface EmailSendResponse {
  sent: number;
  failed: number;
  errors: string[];
  campaign_id: string | null;
}

export interface Campaign {
  id: string;
  subject: string;
  from_email: string;
  from_name: string | null;
  recipient_count: number;
  sent: number;
  failed: number;
  campaign_type: string;
  created_at: string;
}

export interface CampaignListResponse {
  campaigns: Campaign[];
  total: number;
  page: number;
  page_size: number;
}

export interface CampaignFilters {
  campaign_type?: string;
  page?: number;
  page_size?: number;
}

export interface EmailStatus {
  configured: boolean;
}

export function useEmailStatus() {
  return useQuery<EmailStatus>({
    queryKey: ["email-status"],
    queryFn: async ({ signal }) => {
      const res = await api.get("/email-campaigns/status", { signal });
      return res.data;
    },
  });
}

export function useEmailCampaigns(filters: CampaignFilters = {}) {
  return useQuery<CampaignListResponse>({
    queryKey: ["email-campaigns", filters],
    queryFn: async ({ signal }) => {
      const params: Record<string, string | number> = {
        page: filters.page || 1,
        page_size: filters.page_size || 20,
      };
      if (filters.campaign_type) params.campaign_type = filters.campaign_type;

      const res = await api.get("/email-campaigns", { params, signal });
      return res.data;
    },
  });
}

export function useSendEmail() {
  const queryClient = useQueryClient();

  return useMutation<EmailSendResponse, Error, EmailSendRequest>({
    mutationFn: async (data) => {
      const res = await api.post("/email-campaigns/send", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-campaigns"] });
      useToastStore.getState().toast({
        title: "Email sent",
        description: "Your email campaign has been sent successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Send failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}
