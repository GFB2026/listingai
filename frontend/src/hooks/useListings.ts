import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface ListingFilters {
  status?: string;
  property_type?: string;
  city?: string;
  page?: number;
  page_size?: number;
}

export function useListings(filters: ListingFilters = {}) {
  return useQuery({
    queryKey: ["listings", filters],
    queryFn: async () => {
      const params: Record<string, any> = {
        page: filters.page || 1,
        page_size: filters.page_size || 20,
      };
      if (filters.status) params.status = filters.status;
      if (filters.property_type) params.property_type = filters.property_type;
      if (filters.city) params.city = filters.city;

      const res = await api.get("/listings", { params });
      return res.data;
    },
  });
}

export function useListing(id: string) {
  return useQuery({
    queryKey: ["listing", id],
    queryFn: async () => {
      const res = await api.get(`/listings/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}
