import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useSocialStatus, usePublishSocial } from "./useSocial";
import { useToastStore } from "./useToast";

const BASE = "http://localhost:8000/api/v1";

const mockStatus = {
  configured: true,
  facebook: true,
  instagram: false,
};

const mockPostResponse = {
  results: [
    {
      platform: "facebook",
      success: true,
      post_id: "fb-123",
      error: null,
      warning: null,
    },
  ],
};

describe("useSocialStatus", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/social/status`, () =>
        HttpResponse.json(mockStatus)
      )
    );
  });

  it("fetches social status", async () => {
    const { result } = renderHook(() => useSocialStatus(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.configured).toBe(true);
    expect(result.current.data?.facebook).toBe(true);
    expect(result.current.data?.instagram).toBe(false);
  });

  it("handles error", async () => {
    server.use(
      http.get(`${BASE}/social/status`, () => new HttpResponse(null, { status: 500 }))
    );
    const { result } = renderHook(() => useSocialStatus(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("usePublishSocial", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.post(`${BASE}/social/post`, () =>
        HttpResponse.json(mockPostResponse)
      )
    );
  });

  it("posts and shows success toast", async () => {
    const { result } = renderHook(() => usePublishSocial(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        fb_text: "Check out this listing!",
        photo_url: "https://example.com/photo.jpg",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.results).toHaveLength(1);
    expect(result.current.data?.results[0].platform).toBe("facebook");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post(`${BASE}/social/post`, () =>
        HttpResponse.json({ detail: "Facebook token expired" }, { status: 400 })
      )
    );

    const { result } = renderHook(() => usePublishSocial(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        fb_text: "Test post",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});
