import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useLeadSummary, useLeadFunnel } from "./useLeadAnalytics";

const BASE = "http://localhost:8000/api/v1";

const mockSummary = {
  total_leads: 25,
  by_status: { new: 10, contacted: 8, showing: 4, closed: 3 },
  by_source: { google: 12, facebook: 8, direct: 5 },
  by_agent: [
    { agent_name: "Jane Agent", agent_id: "u1", count: 15 },
    { agent_name: "Bob Broker", agent_id: "u2", count: 10 },
  ],
  total_closed_value: 1500000,
};

const mockFunnel = {
  funnel: [
    { status: "new", count: 10, percentage: 40.0 },
    { status: "contacted", count: 8, percentage: 32.0 },
    { status: "showing", count: 4, percentage: 16.0 },
    { status: "under_contract", count: 0, percentage: 0 },
    { status: "closed", count: 3, percentage: 12.0 },
    { status: "lost", count: 0, percentage: 0 },
  ],
  total: 25,
};

describe("useLeadSummary", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/leads/analytics/summary`, () =>
        HttpResponse.json(mockSummary)
      )
    );
  });

  it("fetches lead summary analytics", async () => {
    const { result } = renderHook(() => useLeadSummary(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total_leads).toBe(25);
    expect(result.current.data?.by_status.new).toBe(10);
    expect(result.current.data?.by_agent).toHaveLength(2);
    expect(result.current.data?.total_closed_value).toBe(1500000);
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/leads/analytics/summary`, () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useLeadSummary(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useLeadFunnel", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/leads/analytics/funnel`, () =>
        HttpResponse.json(mockFunnel)
      )
    );
  });

  it("fetches lead funnel data", async () => {
    const { result } = renderHook(() => useLeadFunnel(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total).toBe(25);
    expect(result.current.data?.funnel).toHaveLength(6);
    expect(result.current.data?.funnel[0].status).toBe("new");
    expect(result.current.data?.funnel[0].percentage).toBe(40.0);
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/leads/analytics/funnel`, () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useLeadFunnel(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
