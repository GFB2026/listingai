function getEnv() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl && process.env.NODE_ENV === "production") {
    throw new Error("NEXT_PUBLIC_API_URL is not set. Required in production.");
  }
  return {
    NEXT_PUBLIC_API_URL: apiUrl || "http://localhost:8000",
    NEXT_PUBLIC_SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
  } as const;
}

export const env = getEnv();
