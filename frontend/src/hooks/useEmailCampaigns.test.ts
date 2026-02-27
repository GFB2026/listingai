import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useEmailStatus, useEmailCampaigns, useSendEmail } from "./useEmailCampaigns";
import { useToastStore } from "./useToast";

const BASE = "http://localhost:8000/api/v1";

const mockCampaign = {
  id: "camp-1",
  subject: "New Listing Alert",
  from_email: "broker@realty.com",
  from_name: "Realty Office",
  recipient_count: 5,
  sent: 4,
  failed: 1,
  campaign_type: "just_listed",
  created_at: "2026-02-25T10:00:00Z",
};

describe("useEmailStatus", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/email-campaigns/status`, () =>
        HttpResponse.json({ configured: true })
      )
    );
  });

  it("fetches email status", async () => {
    const { result } = renderHook(() => useEmailStatus(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.configured).toBe(true);
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/email-campaigns/status`, () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useEmailStatus(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useEmailCampaigns", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/email-campaigns`, () =>
        HttpResponse.json({
          campaigns: [mockCampaign],
          total: 1,
          page: 1,
          page_size: 20,
        })
      )
    );
  });

  it("fetches campaign list", async () => {
    const { result } = renderHook(() => useEmailCampaigns(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.campaigns).toHaveLength(1);
    expect(result.current.data?.campaigns[0].subject).toBe("New Listing Alert");
  });

  it("sends default pagination params", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get(`${BASE}/email-campaigns`, ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ campaigns: [], total: 0, page: 1, page_size: 20 });
      })
    );
    const { result } = renderHook(() => useEmailCampaigns(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("page")).toBe("1");
    expect(capturedParams?.get("page_size")).toBe("20");
  });

  it("passes filter params", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get(`${BASE}/email-campaigns`, ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ campaigns: [], total: 0, page: 1, page_size: 20 });
      })
    );
    const { result } = renderHook(
      () => useEmailCampaigns({ campaign_type: "just_listed", page: 2, page_size: 10 }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("campaign_type")).toBe("just_listed");
    expect(capturedParams?.get("page")).toBe("2");
    expect(capturedParams?.get("page_size")).toBe("10");
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/email-campaigns`, () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useEmailCampaigns(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useSendEmail", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.post(`${BASE}/email-campaigns/send`, () =>
        HttpResponse.json({
          sent: 3,
          failed: 0,
          errors: [],
          campaign_id: "camp-2",
        })
      )
    );
  });

  it("sends email and shows success toast", async () => {
    const { result } = renderHook(() => useSendEmail(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        to_emails: ["a@test.com", "b@test.com", "c@test.com"],
        subject: "Open House This Weekend",
        html_content: "<p>Join us!</p>",
        campaign_type: "open_house",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.sent).toBe(3);
    expect(result.current.data?.campaign_id).toBe("camp-2");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post(`${BASE}/email-campaigns/send`, () =>
        HttpResponse.json({ detail: "SendGrid API error" }, { status: 500 })
      )
    );

    const { result } = renderHook(() => useSendEmail(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        to_emails: ["a@test.com"],
        subject: "Test",
        html_content: "<p>Hello</p>",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});
