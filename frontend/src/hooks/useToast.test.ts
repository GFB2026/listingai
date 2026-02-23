import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useToastStore } from "./useToast";
import { act } from "@testing-library/react";

describe("useToastStore", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Clear toasts between tests
    useToastStore.setState({ toasts: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("adds a toast", () => {
    act(() => {
      useToastStore.getState().toast({ title: "Hello" });
    });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    expect(useToastStore.getState().toasts[0].title).toBe("Hello");
  });

  it("assigns sequential string ids", () => {
    act(() => {
      useToastStore.getState().toast({ title: "A" });
      useToastStore.getState().toast({ title: "B" });
    });
    const ids = useToastStore.getState().toasts.map((t) => t.id);
    expect(Number(ids[1])).toBeGreaterThan(Number(ids[0]));
  });

  it("dismiss removes a toast by id", () => {
    act(() => {
      useToastStore.getState().toast({ title: "X" });
    });
    const id = useToastStore.getState().toasts[0].id;
    act(() => {
      useToastStore.getState().dismiss(id);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("remove removes a toast by id", () => {
    act(() => {
      useToastStore.getState().toast({ title: "Y" });
    });
    const id = useToastStore.getState().toasts[0].id;
    act(() => {
      useToastStore.getState().remove(id);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("auto-removes toast after default 5s", () => {
    act(() => {
      useToastStore.getState().toast({ title: "Temp" });
    });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("respects custom duration", () => {
    act(() => {
      useToastStore.getState().toast({ title: "Quick", duration: 1000 });
    });
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(2);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("stores variant", () => {
    act(() => {
      useToastStore.getState().toast({ title: "Err", variant: "error" });
    });
    expect(useToastStore.getState().toasts[0].variant).toBe("error");
  });
});
