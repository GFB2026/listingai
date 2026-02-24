import { describe, it, expect, vi, beforeEach } from "vitest";
import * as Sentry from "@sentry/nextjs";

vi.mock("@sentry/nextjs", () => ({
  init: vi.fn(),
}));

describe("initSentry", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.mocked(Sentry.init).mockClear();
  });

  it("initializes Sentry when DSN is set", async () => {
    const originalEnv = process.env.NEXT_PUBLIC_SENTRY_DSN;
    process.env.NEXT_PUBLIC_SENTRY_DSN = "https://abc@sentry.io/123";
    try {
      const { initSentry } = await import("./sentry");
      initSentry();
      expect(Sentry.init).toHaveBeenCalledWith(
        expect.objectContaining({
          dsn: "https://abc@sentry.io/123",
          sendDefaultPii: false,
        })
      );
    } finally {
      if (originalEnv === undefined) {
        delete process.env.NEXT_PUBLIC_SENTRY_DSN;
      } else {
        process.env.NEXT_PUBLIC_SENTRY_DSN = originalEnv;
      }
    }
  });

  it("skips initialization when DSN is not set", async () => {
    const originalEnv = process.env.NEXT_PUBLIC_SENTRY_DSN;
    delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    try {
      const { initSentry } = await import("./sentry");
      initSentry();
      expect(Sentry.init).not.toHaveBeenCalled();
    } finally {
      if (originalEnv !== undefined) {
        process.env.NEXT_PUBLIC_SENTRY_DSN = originalEnv;
      }
    }
  });
});
