import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useLeads, useLead, useUpdateLead, useDeleteLead, useAddActivity } from "./useLeads";
import { useToastStore } from "./useToast";

const BASE = "http://localhost:8000/api/v1";

const mockLead = {
  id: "lead-1",
  tenant_id: "t1",
  agent_page_id: "ap-1",
  agent_id: "u1",
  listing_id: null,
  first_name: "John",
  last_name: "Doe",
  email: "john@example.com",
  phone: "555-0001",
  message: null,
  property_interest: null,
  pipeline_status: "new",
  utm_source: "google",
  utm_medium: null,
  utm_campaign: null,
  utm_content: null,
  utm_term: null,
  referrer_url: null,
  landing_url: null,
  closed_value: null,
  closed_at: null,
  created_at: "2026-02-20T10:00:00Z",
  updated_at: null,
  agent_name: "Jane Agent",
};

const mockActivity = {
  id: "act-1",
  lead_id: "lead-1",
  user_id: "u1",
  activity_type: "note",
  old_value: null,
  new_value: null,
  note: "Test note",
  created_at: "2026-02-20T10:30:00Z",
  user_name: "Jane Agent",
};

describe("useLeads", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/leads`, () =>
        HttpResponse.json({
          leads: [mockLead],
          total: 1,
          page: 1,
          page_size: 50,
        })
      )
    );
  });

  it("fetches leads list", async () => {
    const { result } = renderHook(() => useLeads(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.leads).toHaveLength(1);
    expect(result.current.data?.leads[0].first_name).toBe("John");
  });

  it("sends default pagination params", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get(`${BASE}/leads`, ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ leads: [], total: 0, page: 1, page_size: 50 });
      })
    );
    const { result } = renderHook(() => useLeads(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("page")).toBe("1");
    expect(capturedParams?.get("page_size")).toBe("50");
  });

  it("passes filter params", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get(`${BASE}/leads`, ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ leads: [], total: 0, page: 1, page_size: 50 });
      })
    );
    const { result } = renderHook(
      () => useLeads({ pipeline_status: "contacted", utm_source: "google", agent_id: "u1" }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("pipeline_status")).toBe("contacted");
    expect(capturedParams?.get("utm_source")).toBe("google");
    expect(capturedParams?.get("agent_id")).toBe("u1");
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/leads`, () => new HttpResponse(null, { status: 500 }))
    );
    const { result } = renderHook(() => useLeads(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useLead", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/leads/:id`, () =>
        HttpResponse.json({
          lead: mockLead,
          activities: [mockActivity],
        })
      )
    );
  });

  it("fetches a single lead by id", async () => {
    const { result } = renderHook(() => useLead("lead-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.lead.first_name).toBe("John");
    expect(result.current.data?.activities).toHaveLength(1);
  });

  it("does not fetch when id is empty", () => {
    const { result } = renderHook(() => useLead(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useUpdateLead", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.patch(`${BASE}/leads/:id`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...mockLead, ...body });
      })
    );
  });

  it("updates lead and shows success toast", async () => {
    const { result } = renderHook(() => useUpdateLead(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ id: "lead-1", pipeline_status: "contacted" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.pipeline_status).toBe("contacted");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.patch(`${BASE}/leads/:id`, () =>
        HttpResponse.json({ detail: "Invalid status" }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useUpdateLead(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ id: "lead-1", pipeline_status: "bad" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useDeleteLead", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.delete(`${BASE}/leads/:id`, () => new HttpResponse(null, { status: 204 }))
    );
  });

  it("deletes lead and shows success toast", async () => {
    const { result } = renderHook(() => useDeleteLead(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("lead-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.delete(`${BASE}/leads/:id`, () => new HttpResponse(null, { status: 500 }))
    );

    const { result } = renderHook(() => useDeleteLead(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("lead-1");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useAddActivity", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.post(`${BASE}/leads/:id/activities`, () =>
        HttpResponse.json(mockActivity, { status: 201 })
      )
    );
  });

  it("adds activity and shows success toast", async () => {
    const { result } = renderHook(() => useAddActivity(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        leadId: "lead-1",
        activity_type: "note",
        note: "Follow up call",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.activity_type).toBe("note");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post(`${BASE}/leads/:id/activities`, () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    const { result } = renderHook(() => useAddActivity(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ leadId: "lead-1", activity_type: "note" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});
