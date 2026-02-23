import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { AuthProvider, useAuth } from "./auth";
import { mockUser } from "@/__tests__/mocks/handlers";

// Track navigation
const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("fetches user on mount", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toEqual(mockUser);
  });

  it("sets user to null on fetch error", async () => {
    server.use(
      http.get("http://localhost:8000/api/v1/auth/me", () =>
        new HttpResponse(null, { status: 500 })
      )
    );
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
  });

  it("starts with isLoading true", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isLoading).toBe(true);
  });
});

describe("login", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("calls POST /auth/login and fetches user", async () => {
    let loginCalled = false;
    server.use(
      http.post("http://localhost:8000/api/v1/auth/login", () => {
        loginCalled = true;
        return HttpResponse.json({ message: "ok" });
      })
    );

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login("test@example.com", "password");
    });

    expect(loginCalled).toBe(true);
    expect(result.current.user).toEqual(mockUser);
  });

  it("navigates to /listings after login", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login("test@example.com", "password");
    });

    expect(pushMock).toHaveBeenCalledWith("/listings");
  });
});

describe("register", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("calls POST /auth/register and navigates to /listings", async () => {
    let registerCalled = false;
    server.use(
      http.post("http://localhost:8000/api/v1/auth/register", () => {
        registerCalled = true;
        return HttpResponse.json({ message: "ok" });
      })
    );

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.register({
        email: "new@example.com",
        password: "pass123",
        full_name: "New User",
        brokerage_name: "Test Realty",
      });
    });

    expect(registerCalled).toBe(true);
    expect(pushMock).toHaveBeenCalledWith("/listings");
  });
});

describe("logout", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("calls POST /auth/logout and clears user", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toEqual(mockUser);

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(pushMock).toHaveBeenCalledWith("/login");
  });

  it("clears state even if API fails", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/auth/logout", () =>
        new HttpResponse(null, { status: 500 })
      )
    );

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(pushMock).toHaveBeenCalledWith("/login");
  });
});

describe("useAuth outside provider", () => {
  it("throws an error", () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within an AuthProvider");
  });
});
