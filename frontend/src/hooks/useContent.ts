import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

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
