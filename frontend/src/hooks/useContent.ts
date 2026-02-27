import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api, { TIMEOUTS } from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

export interface ContentItem {
  id: string;
  content_type: string;
  tone: string | null;
  body: string;
  metadata: Record<string, string | number | string[]>;
  status: string;
  ai_model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  generation_time_ms: number | null;
  version: number;
  listing_id: string | null;
  created_at: string;
}

interface ContentListResponse {
  content: ContentItem[];
  total: number;
  page: number;
  page_size: number;
}

interface ContentFilters {
  content_type?: string;
  listing_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export function useContent(filters: ContentFilters = {}) {
  return useQuery<ContentListResponse>({
    queryKey: ["content", filters],
    queryFn: async ({ signal }) => {
      const params: Record<string, string | number> = {
        page: filters.page || 1,
        page_size: filters.page_size || 20,
      };
      if (filters.content_type) params.content_type = filters.content_type;
      if (filters.listing_id) params.listing_id = filters.listing_id;
      if (filters.status) params.status = filters.status;

      const res = await api.get("/content", { params, signal });
      return res.data;
    },
  });
}

export function useContentItem(id: string) {
  return useQuery<ContentItem>({
    queryKey: ["content", id],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/content/${id}`, { signal });
      return res.data;
    },
    enabled: !!id,
  });
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

interface ContentUpdateData {
  id: string;
  body?: string;
  status?: string;
  metadata?: Record<string, string | number | string[]>;
}

export function useUpdateContent() {
  const queryClient = useQueryClient();

  return useMutation<ContentItem, Error, ContentUpdateData>({
    mutationFn: async ({ id, ...data }) => {
      const res = await api.patch(`/content/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
      useToastStore.getState().toast({
        title: "Content updated",
        description: "Content has been updated successfully.",
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

export function useDeleteContent() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/content/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
      useToastStore.getState().toast({
        title: "Content deleted",
        description: "Content has been deleted successfully.",
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

export function useRegenerateContent() {
  const queryClient = useQueryClient();

  return useMutation<ContentItem, Error, string>({
    mutationFn: async (id) => {
      const res = await api.post(`/content/${id}/regenerate`, {}, { timeout: TIMEOUTS.generate });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
      queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
      useToastStore.getState().toast({
        title: "Content regenerated",
        description: "Content has been regenerated successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Regeneration failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}
