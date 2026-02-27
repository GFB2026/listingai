import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import {
  useUsers,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
} from "./useUsers";
import { useToastStore } from "./useToast";

const BASE = "http://localhost:8000/api/v1";

const mockUser = {
  id: "u-1",
  email: "jane@realty.com",
  full_name: "Jane Agent",
  role: "agent",
  is_active: true,
  created_at: "2026-02-20T10:00:00Z",
};

describe("useUsers", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/users`, () =>
        HttpResponse.json({
          users: [mockUser],
          total: 1,
        })
      )
    );
  });

  it("fetches user list", async () => {
    const { result } = renderHook(() => useUsers(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.users).toHaveLength(1);
    expect(result.current.data?.users[0].email).toBe("jane@realty.com");
  });
});

describe("useCreateUser", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.post(`${BASE}/users`, () =>
        HttpResponse.json(mockUser, { status: 201 })
      )
    );
  });

  it("creates user and shows success toast", async () => {
    const { result } = renderHook(() => useCreateUser(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        email: "jane@realty.com",
        password: "securepass123",
        full_name: "Jane Agent",
        role: "agent",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.email).toBe("jane@realty.com");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post(`${BASE}/users`, () =>
        HttpResponse.json({ detail: "Email already in use" }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useCreateUser(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        email: "taken@realty.com",
        password: "securepass123",
        full_name: "Duplicate User",
        role: "agent",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useUpdateUser", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.patch(`${BASE}/users/:id`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...mockUser, ...body });
      })
    );
  });

  it("updates user and shows success toast", async () => {
    const { result } = renderHook(() => useUpdateUser(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ id: "u-1", role: "broker" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.role).toBe("broker");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });
});

describe("useDeleteUser", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.delete(`${BASE}/users/:id`, () =>
        new HttpResponse(null, { status: 204 })
      )
    );
  });

  it("deletes user and shows success toast", async () => {
    const { result } = renderHook(() => useDeleteUser(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("u-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });
});
