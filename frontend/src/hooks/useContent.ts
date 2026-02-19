import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface ContentFilters {
  content_type?: string;
  listing_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export function useContent(filters: ContentFilters = {}) {
  return useQuery({
    queryKey: ["content", filters],
    queryFn: async () => {
      const params: Record<string, any> = {
        page: filters.page || 1,
        page_size: filters.page_size || 20,
      };
      if (filters.content_type) params.content_type = filters.content_type;
      if (filters.listing_id) params.listing_id = filters.listing_id;
      if (filters.status) params.status = filters.status;

      const res = await api.get("/content", { params });
      return res.data;
    },
  });
}

export function useContentItem(id: string) {
  return useQuery({
    queryKey: ["content", id],
    queryFn: async () => {
      const res = await api.get(`/content/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}
