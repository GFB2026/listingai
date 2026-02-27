import { useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api, { TIMEOUTS } from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

interface GenerateRequest {
  listing_id: string;
  content_type: string;
  tone: string;
  brand_profile_id?: string | null;
  instructions?: string;
  event_details?: string;
  variants: number;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

export function useGenerate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: GenerateRequest) => {
      const res = await api.post("/content/generate", request, {
        timeout: TIMEOUTS.generate,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
      queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
      useToastStore.getState().toast({
        title: "Content generated",
        description: "Your content has been generated successfully.",
        variant: "success",
      });
    },
    onError: (error: unknown) => {
      useToastStore.getState().toast({
        title: "Generation failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}
