import axios from "axios";
import { env } from "./env";

const api = axios.create({
  baseURL: `${env.NEXT_PUBLIC_API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
  timeout: 30_000, // default 30s; override per-request for long operations
});

/**
 * Timeout presets for different operation types.
 * Pass as { timeout: TIMEOUTS.generate } in request config.
 */
export const TIMEOUTS = {
  default: 30_000,
  generate: 120_000,  // AI content generation can take up to 90s
  batch: 10_000,      // batch queues immediately; just a POST
  upload: 60_000,     // media uploads
} as const;

// Helper to read a cookie value by name
function getCookie(name: string): string | undefined {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

// Request interceptor: attach request ID + CSRF token
api.interceptors.request.use((config) => {
  config.headers["X-Request-ID"] = crypto.randomUUID();

  // Attach CSRF token for state-changing requests
  const method = config.method?.toUpperCase();
  if (method && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCookie("csrf_token");
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }

  return config;
});

// Singleton refresh promise to prevent concurrent refresh attempts
let refreshPromise: Promise<void> | null = null;

// Response interceptor: handle 401 with cookie-based token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (!refreshPromise) {
        refreshPromise = axios
          .post(
            `${env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
            {},
            { withCredentials: true, timeout: 10_000 }
          )
          .then(() => {})
          .catch(() => {
            window.location.href = "/login";
          })
          .finally(() => {
            refreshPromise = null;
          });
      }

      await refreshPromise;
      return api(originalRequest);
    }

    return Promise.reject(error);
  }
);

export default api;
