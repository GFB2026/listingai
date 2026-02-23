import { create } from "zustand";

export type ToastVariant = "default" | "success" | "error" | "warning";

export interface ToastItem {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastState {
  toasts: ToastItem[];
  toast: (item: Omit<ToastItem, "id">) => void;
  dismiss: (id: string) => void;
  remove: (id: string) => void;
}

let toastCount = 0;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  toast: (item) => {
    const id = String(++toastCount);
    set((state) => ({
      toasts: [...state.toasts, { id, ...item }],
    }));
    // Auto-remove after duration
    const duration = item.duration ?? 5000;
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, duration);
  },
  dismiss: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
  remove: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
}));

export function useToast() {
  return useToastStore();
}
