import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

export interface Listing {
  id: string;
  address_full: string;
  address_street: string | null;
  address_city: string | null;
  address_state: string | null;
  address_zip: string | null;
  price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  lot_sqft: number | null;
  year_built: number | null;
  property_type: string | null;
  status: string | null;
  description_original: string | null;
  features: string[];
  photos: Array<{ url: string; caption?: string }>;
  listing_agent_id: string | null;
  listing_agent_name: string | null;
  listing_agent_email?: string;
  listing_agent_phone?: string;
  previous_price?: number | null;
  close_price?: number | null;
  close_date?: string | null;
  mls_listing_id: string | null;
  created_at: string;
}

interface ListingListResponse {
  listings: Listing[];
  total: number;
  page: number;
  page_size: number;
}

interface ListingFilters {
  status?: string;
  property_type?: string;
  city?: string;
  min_price?: string;
  max_price?: string;
  bedrooms?: string;
  bathrooms?: string;
  page?: number;
  page_size?: number;
}

export function useListings(filters: ListingFilters = {}) {
  return useQuery<ListingListResponse>({
    queryKey: ["listings", filters],
    queryFn: async ({ signal }) => {
      const params: Record<string, string | number> = {
        page: filters.page || 1,
        page_size: filters.page_size || 20,
      };
      if (filters.status) params.status = filters.status;
      if (filters.property_type) params.property_type = filters.property_type;
      if (filters.city) params.city = filters.city;
      if (filters.min_price) params.min_price = filters.min_price;
      if (filters.max_price) params.max_price = filters.max_price;
      if (filters.bedrooms) params.bedrooms = filters.bedrooms;
      if (filters.bathrooms) params.bathrooms = filters.bathrooms;

      const res = await api.get("/listings", { params, signal });
      return res.data;
    },
  });
}

export function useListing(id: string) {
  return useQuery<Listing>({
    queryKey: ["listing", id],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/listings/${id}`, { signal });
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

export interface ListingCreateData {
  address_full: string;
  address_street?: string;
  address_city?: string;
  address_state?: string;
  address_zip?: string;
  price?: number;
  bedrooms?: number;
  bathrooms?: number;
  sqft?: number;
  lot_sqft?: number;
  year_built?: number;
  property_type?: string;
  status?: string;
  description_original?: string;
  features?: string[];
}

export function useCreateListing() {
  const queryClient = useQueryClient();

  return useMutation<Listing, Error, ListingCreateData>({
    mutationFn: async (data) => {
      const res = await api.post("/listings/manual", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["listings"] });
      useToastStore.getState().toast({
        title: "Listing created",
        description: "Listing has been created successfully.",
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
