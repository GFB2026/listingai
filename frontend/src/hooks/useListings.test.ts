import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useListings, useListing } from "./useListings";
import { mockListing } from "@/__tests__/mocks/handlers";

describe("useListings", () => {
  it("fetches listings", async () => {
    const { result } = renderHook(() => useListings(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.listings).toHaveLength(1);
    expect(result.current.data?.listings[0].id).toBe(mockListing.id);
  });

  it("sends default page=1, page_size=20", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get("http://localhost:8000/api/v1/listings", ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ listings: [], total: 0, page: 1, page_size: 20 });
      })
    );
    const { result } = renderHook(() => useListings(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("page")).toBe("1");
    expect(capturedParams?.get("page_size")).toBe("20");
  });

  it("passes filter params", async () => {
    let capturedParams: URLSearchParams | undefined;
    server.use(
      http.get("http://localhost:8000/api/v1/listings", ({ request }) => {
        capturedParams = new URL(request.url).searchParams;
        return HttpResponse.json({ listings: [], total: 0, page: 1, page_size: 20 });
      })
    );
    const { result } = renderHook(
      () =>
        useListings({
          status: "active",
          city: "Miami",
          property_type: "condo",
          min_price: "100000",
          max_price: "500000",
          bedrooms: "3",
          bathrooms: "2",
        }),
      { wrapper: createWrapper() }
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedParams?.get("status")).toBe("active");
    expect(capturedParams?.get("city")).toBe("Miami");
    expect(capturedParams?.get("property_type")).toBe("condo");
    expect(capturedParams?.get("min_price")).toBe("100000");
    expect(capturedParams?.get("max_price")).toBe("500000");
    expect(capturedParams?.get("bedrooms")).toBe("3");
    expect(capturedParams?.get("bathrooms")).toBe("2");
  });

  it("handles error", async () => {
    server.use(
      http.get("http://localhost:8000/api/v1/listings", () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useListings(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useListing", () => {
  it("fetches a single listing by id", async () => {
    const { result } = renderHook(() => useListing("lst-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("lst-1");
  });

  it("does not fetch when id is empty", () => {
    const { result } = renderHook(() => useListing(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});
