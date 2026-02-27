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

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserListResponse {
  users: UserResponse[];
  total: number;
}

interface UserCreateData {
  email: string;
  password: string;
  full_name: string;
  role: string;
}

interface UserUpdateData {
  id: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
}

export function useUsers() {
  return useQuery<UserListResponse>({
    queryKey: ["users"],
    queryFn: async ({ signal }) => {
      const res = await api.get("/users", { signal });
      return res.data;
    },
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation<UserResponse, Error, UserCreateData>({
    mutationFn: async (data) => {
      const res = await api.post("/users", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      useToastStore.getState().toast({
        title: "User created",
        description: "New team member has been added successfully.",
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

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation<UserResponse, Error, UserUpdateData>({
    mutationFn: async ({ id, ...data }) => {
      const res = await api.patch(`/users/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      useToastStore.getState().toast({
        title: "User updated",
        description: "Team member has been updated successfully.",
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

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await api.delete(`/users/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      useToastStore.getState().toast({
        title: "User deleted",
        description: "Team member has been removed.",
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
