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

export interface SocialPostRequest {
  listing_id?: string;
  content_id?: string;
  fb_text?: string;
  ig_text?: string;
  photo_url?: string;
  listing_link?: string;
}

export interface SocialPostResult {
  platform: string;
  success: boolean;
  post_id: string | null;
  error: string | null;
  warning: string | null;
}

export interface SocialPostResponse {
  results: SocialPostResult[];
}

export interface SocialStatus {
  configured: boolean;
  facebook: boolean;
  instagram: boolean;
}

export function useSocialStatus() {
  return useQuery<SocialStatus>({
    queryKey: ["social-status"],
    queryFn: async ({ signal }) => {
      const res = await api.get("/social/status", { signal });
      return res.data;
    },
  });
}

export function usePublishSocial() {
  const queryClient = useQueryClient();

  return useMutation<SocialPostResponse, Error, SocialPostRequest>({
    mutationFn: async (data) => {
      const res = await api.post("/social/post", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["social-status"] });
      useToastStore.getState().toast({
        title: "Post published",
        description: "Your social media post has been published successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Publish failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}
