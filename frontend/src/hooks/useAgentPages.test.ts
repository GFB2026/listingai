import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import {
  useAgentPages,
  useCreateAgentPage,
  useUpdateAgentPage,
  useDeleteAgentPage,
} from "./useAgentPages";
import { useToastStore } from "./useToast";

const BASE = "http://localhost:8000/api/v1";

const mockAgentPage = {
  id: "ap-1",
  tenant_id: "t1",
  user_id: "u1",
  slug: "jane-agent",
  headline: "Your Dream Home Awaits",
  bio: "Top-producing agent.",
  photo_url: null,
  phone: "555-0100",
  email_display: "jane@realty.com",
  is_active: true,
  theme: null,
  created_at: "2026-02-15T10:00:00Z",
  updated_at: null,
  user_name: "Jane Agent",
};

describe("useAgentPages", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/agent-pages`, () =>
        HttpResponse.json({
          agent_pages: [mockAgentPage],
          total: 1,
        })
      )
    );
  });

  it("fetches agent pages", async () => {
    const { result } = renderHook(() => useAgentPages(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.agent_pages).toHaveLength(1);
    expect(result.current.data?.agent_pages[0].slug).toBe("jane-agent");
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/agent-pages`, () => new HttpResponse(null, { status: 500 }))
    );
    const { result } = renderHook(() => useAgentPages(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreateAgentPage", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.post(`${BASE}/agent-pages`, () =>
        HttpResponse.json(mockAgentPage, { status: 201 })
      )
    );
  });

  it("creates agent page and shows success toast", async () => {
    const { result } = renderHook(() => useCreateAgentPage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        user_id: "u1",
        slug: "jane-agent",
        headline: "Your Dream Home Awaits",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.slug).toBe("jane-agent");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post(`${BASE}/agent-pages`, () =>
        HttpResponse.json({ detail: "Slug already in use" }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useCreateAgentPage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        user_id: "u1",
        slug: "taken-slug",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useUpdateAgentPage", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.patch(`${BASE}/agent-pages/:id`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...mockAgentPage, ...body });
      })
    );
  });

  it("updates agent page and shows success toast", async () => {
    const { result } = renderHook(() => useUpdateAgentPage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ id: "ap-1", headline: "Updated Headline" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.headline).toBe("Updated Headline");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.patch(`${BASE}/agent-pages/:id`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 })
      )
    );

    const { result } = renderHook(() => useUpdateAgentPage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ id: "ap-999", headline: "Ghost" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useDeleteAgentPage", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.delete(`${BASE}/agent-pages/:id`, () =>
        new HttpResponse(null, { status: 204 })
      )
    );
  });

  it("deletes agent page and shows success toast", async () => {
    const { result } = renderHook(() => useDeleteAgentPage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("ap-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.delete(`${BASE}/agent-pages/:id`, () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    const { result } = renderHook(() => useDeleteAgentPage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("ap-1");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});
