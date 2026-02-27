import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api, { TIMEOUTS } from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

export interface MediaUploadResponse {
  media_id: string;
  key: string;
  content_type: string;
  size: number;
}

export interface MediaPresignedResponse {
  url: string | null;
  media_id: string;
  key: string | null;
  error: string | null;
}

export function useUploadMedia() {
  const queryClient = useQueryClient();

  return useMutation<MediaUploadResponse, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/media/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: TIMEOUTS.upload,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media"] });
      useToastStore.getState().toast({
        title: "File uploaded",
        description: "File has been uploaded successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Upload failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}

export function useMediaUrl(mediaId: string | null | undefined) {
  return useQuery<MediaPresignedResponse>({
    queryKey: ["media", mediaId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/media/${mediaId}`, { signal });
      return res.data;
    },
    enabled: !!mediaId,
  });
}
