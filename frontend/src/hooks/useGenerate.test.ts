import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import { useGenerate } from "./useGenerate";
import { useToastStore } from "./useToast";

const generateRequest = {
  listing_id: "lst-1",
  content_type: "listing_description",
  tone: "luxury",
  variants: 1,
};

describe("useGenerate", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("posts to /content/generate", async () => {
    let capturedBody: unknown;
    server.use(
      http.post("http://localhost:8000/api/v1/content/generate", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json([{ id: "c1", body: "Generated" }]);
      })
    );

    const { result } = renderHook(() => useGenerate(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate(generateRequest);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedBody).toMatchObject({
      listing_id: "lst-1",
      content_type: "listing_description",
    });
  });

  it("shows success toast on success", async () => {
    const { result } = renderHook(() => useGenerate(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate(generateRequest);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/content/generate", () =>
        HttpResponse.json({ detail: "Insufficient credits" }, { status: 402 })
      )
    );

    const { result } = renderHook(() => useGenerate(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate(generateRequest);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });

  it("uses 120s timeout", async () => {
    let receivedRequest = false;
    server.use(
      http.post("http://localhost:8000/api/v1/content/generate", () => {
        receivedRequest = true;
        return HttpResponse.json([{ id: "c1", body: "ok" }]);
      })
    );

    const { result } = renderHook(() => useGenerate(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate(generateRequest);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(receivedRequest).toBe(true);
  });
});
