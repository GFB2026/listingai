import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

interface GenerateRequest {
  listing_id: string;
  content_type: string;
  tone: string;
  brand_profile_id?: string | null;
  instructions?: string;
  variants: number;
}

export function useGenerate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: GenerateRequest) => {
      const res = await api.post("/content/generate", request);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content"] });
      queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
    },
  });
}
