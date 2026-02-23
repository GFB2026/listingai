import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useContent, useContentItem } from "./useContent";
import { mockContentItem } from "@/__tests__/mocks/handlers";

describe("useContent", () => {
  it("fetches content list", async () => {
    const { result } = renderHook(() => useContent(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.content).toHaveLength(1);
    expect(result.current.data?.content[0].id).toBe(mockContentItem.id);
  });

  it("sends default pagination params", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get("http://localhost:8000/api/v1/content", ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ content: [], total: 0, page: 1, page_size: 20 });
      })
    );
    const { result } = renderHook(() => useContent(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("page")).toBe("1");
    expect(capturedParams?.get("page_size")).toBe("20");
  });

  it("passes content_type and listing_id filters", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get("http://localhost:8000/api/v1/content", ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ content: [], total: 0, page: 1, page_size: 20 });
      })
    );
    const { result } = renderHook(
      () => useContent({ content_type: "social_instagram", listing_id: "lst-1" }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("content_type")).toBe("social_instagram");
    expect(capturedParams?.get("listing_id")).toBe("lst-1");
  });

  it("handles error", async () => {
    server.use(
      http.get("http://localhost:8000/api/v1/content", () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useContent(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useContentItem", () => {
  it("fetches a single content item", async () => {
    const { result } = renderHook(() => useContentItem("c1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("c1");
    expect(result.current.data?.body).toBe(mockContentItem.body);
  });

  it("does not fetch when id is empty", () => {
    const { result } = renderHook(() => useContentItem(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});
