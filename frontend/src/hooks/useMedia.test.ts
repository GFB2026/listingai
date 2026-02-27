import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useUploadMedia, useMediaUrl } from "./useMedia";
import { useToastStore } from "./useToast";

const BASE = "http://localhost:8000/api/v1";

const mockUploadResponse = {
  media_id: "m-1",
  key: "tenants/t1/uploads/photo.jpg",
  content_type: "image/jpeg",
  size: 204800,
};

const mockPresignedResponse = {
  url: "https://s3.amazonaws.com/bucket/tenants/t1/uploads/photo.jpg?signed=abc",
  media_id: "m-1",
  key: "tenants/t1/uploads/photo.jpg",
  error: null,
};

describe("useUploadMedia", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    server.use(
      http.post(`${BASE}/media/upload`, () =>
        HttpResponse.json(mockUploadResponse, { status: 201 })
      )
    );
  });

  it("uploads file and shows success toast", async () => {
    const { result } = renderHook(() => useUploadMedia(), {
      wrapper: createWrapper(),
    });

    const file = new File(["test-content"], "photo.jpg", {
      type: "image/jpeg",
    });

    await act(async () => {
      result.current.mutate(file);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.media_id).toBe("m-1");
    expect(result.current.data?.key).toBe("tenants/t1/uploads/photo.jpg");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post(`${BASE}/media/upload`, () =>
        HttpResponse.json(
          { detail: "File too large" },
          { status: 413 }
        )
      )
    );

    const { result } = renderHook(() => useUploadMedia(), {
      wrapper: createWrapper(),
    });

    const file = new File(["big-content"], "huge.jpg", {
      type: "image/jpeg",
    });

    await act(async () => {
      result.current.mutate(file);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useMediaUrl", () => {
  beforeEach(() => {
    server.use(
      http.get(`${BASE}/media/:mediaId`, () =>
        HttpResponse.json(mockPresignedResponse)
      )
    );
  });

  it("fetches presigned URL", async () => {
    const { result } = renderHook(() => useMediaUrl("m-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.url).toContain("s3.amazonaws.com");
    expect(result.current.data?.media_id).toBe("m-1");
    expect(result.current.data?.error).toBeNull();
  });

  it("does not fetch when mediaId is falsy", () => {
    const { result } = renderHook(() => useMediaUrl(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
  });
});
