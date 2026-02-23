import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";

// We must import api fresh — it reads env at import time
let api: typeof import("./api").default;
let TIMEOUTS: typeof import("./api").TIMEOUTS;

beforeEach(async () => {
  // Dynamic import to get the module with interceptors attached
  const mod = await import("./api");
  api = mod.default;
  TIMEOUTS = mod.TIMEOUTS;
});

describe("api instance config", () => {
  it("has baseURL pointing to /api/v1", () => {
    expect(api.defaults.baseURL).toContain("/api/v1");
  });

  it("sends credentials (cookies) by default", () => {
    expect(api.defaults.withCredentials).toBe(true);
  });

  it("has a 30s default timeout", () => {
    expect(api.defaults.timeout).toBe(30_000);
  });
});

describe("TIMEOUTS", () => {
  it("defines expected presets", () => {
    expect(TIMEOUTS.default).toBe(30_000);
    expect(TIMEOUTS.generate).toBe(120_000);
    expect(TIMEOUTS.batch).toBe(10_000);
    expect(TIMEOUTS.upload).toBe(60_000);
  });
});

describe("request interceptor", () => {
  it("attaches X-Request-ID to every request", async () => {
    let requestId: string | undefined;
    server.use(
      http.get("http://localhost:8000/api/v1/test-headers", ({ request }) => {
        requestId = request.headers.get("X-Request-ID") ?? undefined;
        return HttpResponse.json({ ok: true });
      })
    );
    await api.get("/test-headers");
    expect(requestId).toBeDefined();
    expect(requestId!.length).toBeGreaterThan(0);
  });

  it("attaches X-CSRF-Token for POST requests when cookie exists", async () => {
    // Set a csrf cookie
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "csrf_token=abc123",
    });

    let csrfHeader: string | undefined;
    server.use(
      http.post("http://localhost:8000/api/v1/test-csrf", ({ request }) => {
        csrfHeader = request.headers.get("X-CSRF-Token") ?? undefined;
        return HttpResponse.json({ ok: true });
      })
    );

    await api.post("/test-csrf", {});
    expect(csrfHeader).toBe("abc123");

    // Cleanup
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });
  });

  it("does NOT attach CSRF token for GET requests", async () => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "csrf_token=abc123",
    });

    let csrfHeader: string | null = null;
    server.use(
      http.get("http://localhost:8000/api/v1/test-no-csrf", ({ request }) => {
        csrfHeader = request.headers.get("X-CSRF-Token");
        return HttpResponse.json({ ok: true });
      })
    );

    await api.get("/test-no-csrf");
    expect(csrfHeader).toBeNull();

    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });
  });
});

describe("401 response interceptor", () => {
  it("attempts token refresh then retries the original request", async () => {
    let callCount = 0;
    server.use(
      http.get("http://localhost:8000/api/v1/protected", () => {
        callCount++;
        if (callCount === 1) {
          return new HttpResponse(null, { status: 401 });
        }
        return HttpResponse.json({ data: "ok" });
      }),
      http.post("http://localhost:8000/api/v1/auth/refresh", () =>
        HttpResponse.json({ message: "refreshed" })
      )
    );

    const res = await api.get("/protected");
    expect(res.data).toEqual({ data: "ok" });
    expect(callCount).toBe(2);
  });

  it("redirects to /login when refresh also fails", async () => {
    const originalHref = window.location.href;
    // Mock window.location
    const locationSpy = vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      href: originalHref,
    } as Location);

    // Use defineProperty to make href settable
    let capturedHref = "";
    Object.defineProperty(window, "location", {
      writable: true,
      value: {
        ...window.location,
        get href() {
          return capturedHref || originalHref;
        },
        set href(val: string) {
          capturedHref = val;
        },
      },
    });

    server.use(
      http.get("http://localhost:8000/api/v1/fail-auth", () =>
        new HttpResponse(null, { status: 401 })
      ),
      http.post("http://localhost:8000/api/v1/auth/refresh", () =>
        new HttpResponse(null, { status: 401 })
      )
    );

    try {
      await api.get("/fail-auth");
    } catch {
      // Expected to fail
    }

    // Give the async catch handler time to execute
    await new Promise((r) => setTimeout(r, 50));
    expect(capturedHref).toBe("/login");

    locationSpy.mockRestore();
  });
});
