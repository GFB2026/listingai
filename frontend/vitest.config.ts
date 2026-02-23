import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/lib/**", "src/hooks/**", "src/components/**"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/__tests__/**"],
      thresholds: {
        "src/lib/**": { statements: 70 },
        "src/hooks/**": { statements: 70 },
      },
    },
  },
});
