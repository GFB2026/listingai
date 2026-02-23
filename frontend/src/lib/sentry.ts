import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

export function initSentry() {
  if (!SENTRY_DSN) return;

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,
    tracesSampleRate: 0.1,
    // Don't send PII
    sendDefaultPii: false,
    // Filter out noisy errors
    ignoreErrors: [
      "ResizeObserver loop",
      "Network Error",
      "Load failed",
      "AbortError",
    ],
  });
}
