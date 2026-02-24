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

export interface AgentPage {
  id: string;
  tenant_id: string;
  user_id: string;
  slug: string;
  headline: string | null;
  bio: string | null;
  photo_url: string | null;
  phone: string | null;
  email_display: string | null;
  theme: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  user_name: string | null;
}

interface AgentPageListResponse {
  agent_pages: AgentPage[];
  total: number;
}

interface AgentPageCreateData {
  user_id: string;
  slug: string;
  headline?: string;
  bio?: string;
  photo_url?: string;
  phone?: string;
  email_display?: string;
  theme?: string;
}

interface AgentPageUpdateData {
  id: string;
  slug?: string;
  headline?: string;
  bio?: string;
  photo_url?: string;
  phone?: string;
  email_display?: string;
  theme?: string;
  is_active?: boolean;
}

export function useAgentPages() {
  return useQuery<AgentPageListResponse>({
    queryKey: ["agent-pages"],
    queryFn: async ({ signal }) => {
      const res = await api.get("/agent-pages", { signal });
      return res.data;
    },
  });
}

export function useCreateAgentPage() {
  const queryClient = useQueryClient();

  return useMutation<AgentPage, Error, AgentPageCreateData>({
    mutationFn: async (data) => {
      const res = await api.post("/agent-pages", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-pages"] });
      useToastStore.getState().toast({
        title: "Agent page created",
        description: "Agent landing page has been created successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Creation failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}

export function useUpdateAgentPage() {
  const queryClient = useQueryClient();

  return useMutation<AgentPage, Error, AgentPageUpdateData>({
    mutationFn: async ({ id, ...data }) => {
      const res = await api.patch(`/agent-pages/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-pages"] });
      useToastStore.getState().toast({
        title: "Agent page updated",
        description: "Agent landing page has been updated successfully.",
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

export function useDeleteAgentPage() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/agent-pages/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-pages"] });
      useToastStore.getState().toast({
        title: "Agent page deactivated",
        description: "Agent landing page has been deactivated.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Deactivation failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}
