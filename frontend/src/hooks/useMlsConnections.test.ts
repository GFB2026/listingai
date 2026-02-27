import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { createWrapper } from "@/__tests__/test-utils";
import {
  useMlsConnections,
  useMlsConnectionStatus,
  useCreateMlsConnection,
  useUpdateMlsConnection,
  useTestMlsConnection,
  useDeleteMlsConnection,
} from "./useMlsConnections";
import { useToastStore } from "./useToast";
import { mockMlsConnection } from "@/__tests__/mocks/handlers";

describe("useMlsConnections", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("fetches connections list", async () => {
    const { result } = renderHook(() => useMlsConnections(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.connections).toHaveLength(1);
    expect(result.current.data?.connections[0].id).toBe(mockMlsConnection.id);
  });

  it("handles error", async () => {
    server.use(
      http.get("http://localhost:8000/api/v1/mls-connections", () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useMlsConnections(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useMlsConnectionStatus", () => {
  it("fetches status when connectionId is provided", async () => {
    const { result } = renderHook(() => useMlsConnectionStatus("mls-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.listing_count).toBe(42);
  });

  it("does not fetch when connectionId is null", () => {
    const { result } = renderHook(() => useMlsConnectionStatus(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useCreateMlsConnection", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("posts new connection and shows success toast", async () => {
    const { result } = renderHook(() => useCreateMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        provider: "reso",
        name: "Test MLS",
        base_url: "https://api.test.com",
        client_id: "id",
        client_secret: "secret",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on failure", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/mls-connections", () =>
        HttpResponse.json({ detail: "Invalid" }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useCreateMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        provider: "reso",
        name: "Bad",
        base_url: "https://bad.com",
        client_id: "x",
        client_secret: "x",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useUpdateMlsConnection", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("updates connection and shows success toast", async () => {
    const { result } = renderHook(() => useUpdateMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        id: "mls-1",
        name: "Updated MLS",
        sync_enabled: false,
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on update failure", async () => {
    server.use(
      http.patch("http://localhost:8000/api/v1/mls-connections/:id", () =>
        HttpResponse.json({ detail: "Invalid" }, { status: 400 })
      )
    );

    const { result } = renderHook(() => useUpdateMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        id: "mls-1",
        name: "Bad Update",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useTestMlsConnection", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("tests a connection and returns result", async () => {
    const { result } = renderHook(() => useTestMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("mls-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.success).toBe(true);
    expect(result.current.data?.property_count).toBe(42);
  });

  it("shows error toast on test failure", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/mls-connections/:id/test", () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    const { result } = renderHook(() => useTestMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("mls-1");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});

describe("useDeleteMlsConnection", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
  });

  it("deletes a connection and shows success toast", async () => {
    const { result } = renderHook(() => useDeleteMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("mls-1");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "success")).toBe(true);
  });

  it("shows error toast on delete failure", async () => {
    server.use(
      http.delete("http://localhost:8000/api/v1/mls-connections/:id", () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    const { result } = renderHook(() => useDeleteMlsConnection(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate("mls-1");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    const toasts = useToastStore.getState().toasts;
    expect(toasts.some((t) => t.variant === "error")).toBe(true);
  });
});
