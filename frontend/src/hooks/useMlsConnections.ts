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

interface MLSConnection {
  id: string;
  provider: string;
  name: string | null;
  base_url: string;
  sync_enabled: boolean;
  last_sync_at: string | null;
  created_at: string;
}

interface MLSConnectionCreate {
  provider: string;
  name: string;
  base_url: string;
  client_id: string;
  client_secret: string;
  sync_enabled?: boolean;
}

interface TestResult {
  success: boolean;
  message: string;
  property_count: number | null;
}

interface ConnectionStatus {
  id: string;
  name: string | null;
  sync_enabled: boolean;
  last_sync_at: string | null;
  sync_watermark: string | null;
  listing_count: number;
}

export function useMlsConnections() {
  return useQuery<{ connections: MLSConnection[] }>({
    queryKey: ["mls-connections"],
    queryFn: async () => {
      const res = await api.get("/mls-connections");
      return res.data;
    },
  });
}

export function useMlsConnectionStatus(connectionId: string | null) {
  return useQuery<ConnectionStatus>({
    queryKey: ["mls-connections", connectionId, "status"],
    queryFn: async () => {
      const res = await api.get(`/mls-connections/${connectionId}/status`);
      return res.data;
    },
    enabled: !!connectionId,
  });
}

export function useCreateMlsConnection() {
  const queryClient = useQueryClient();

  return useMutation<MLSConnection, Error, MLSConnectionCreate>({
    mutationFn: async (data) => {
      const res = await api.post("/mls-connections", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mls-connections"] });
      useToastStore.getState().toast({
        title: "Connection created",
        description: "MLS connection has been created successfully.",
        variant: "success",
      });
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Connection failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}

export function useTestMlsConnection() {
  return useMutation<TestResult, Error, string>({
    mutationFn: async (connectionId) => {
      const res = await api.post(`/mls-connections/${connectionId}/test`);
      return res.data;
    },
    onError: (error: Error) => {
      useToastStore.getState().toast({
        title: "Connection test failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });
}

export function useDeleteMlsConnection() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (connectionId) => {
      await api.delete(`/mls-connections/${connectionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mls-connections"] });
      useToastStore.getState().toast({
        title: "Connection deleted",
        description: "MLS connection has been removed.",
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
