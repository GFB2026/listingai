import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = "http://localhost:8000/api/v1";

const FAKE_USER = {
  id: "u_test_1",
  email: "agent@example.com",
  full_name: "Test Agent",
  role: "admin",
  tenant_id: "t_test_1",
  is_active: true,
};

/**
 * Intercept `/auth/me` to simulate an unauthenticated session.
 */
async function mockUnauthenticated(page: import("@playwright/test").Page) {
  await page.route(`${API_BASE}/auth/me`, (route) =>
    route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) }),
  );
}

/**
 * Intercept auth endpoints to simulate a fully authenticated session.
 * - POST /auth/login  -> 200
 * - GET  /auth/me     -> current user
 * - POST /auth/logout -> 200
 *
 * Also stubs the dashboard data calls so the page renders after redirect.
 */
async function mockAuthenticated(page: import("@playwright/test").Page) {
  await page.route(`${API_BASE}/auth/login`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: "ok" }) }),
  );

  await page.route(`${API_BASE}/auth/me`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_USER) }),
  );

  await page.route(`${API_BASE}/auth/logout`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: "ok" }) }),
  );

  // Stub dashboard data calls so the page doesn't hang
  await page.route(`${API_BASE}/billing/usage`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ credits_used: 5, credits_limit: 100, credits_remaining: 95, plan: "starter" }),
    }),
  );

  await page.route(`${API_BASE}/listings**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ listings: [], total: 0 }) }),
  );

  await page.route(`${API_BASE}/content**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ content: [], total: 0 }) }),
  );

  await page.route(`${API_BASE}/leads**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ leads: [], total: 0 }) }),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Authentication", () => {
  test("visiting / redirects to /login when not authenticated", async ({ page }) => {
    await mockUnauthenticated(page);

    await page.goto("/");
    await page.waitForURL("**/login");

    await expect(page).toHaveURL(/\/login/);
  });

  test("login with valid credentials redirects to the listings page", async ({ page }) => {
    // Start unauthenticated so the login page renders
    let loginAttempted = false;

    await page.route(`${API_BASE}/auth/me`, (route) => {
      if (!loginAttempted) {
        return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) });
      }
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_USER) });
    });

    await page.route(`${API_BASE}/auth/login`, (route) => {
      loginAttempted = true;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: "ok" }) });
    });

    // Stub post-login data calls
    await page.route(`${API_BASE}/listings**`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ listings: [], total: 0 }) }),
    );
    await page.route(`${API_BASE}/mls/connections**`, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ connections: [] }) }),
    );

    await page.goto("/login");

    // Fill in the login form
    await page.getByLabel("Email").fill("agent@example.com");
    await page.getByLabel("Password").fill("password123");
    await page.getByRole("button", { name: "Sign In" }).click();

    // After login the app redirects to /listings
    await page.waitForURL("**/listings");
    await expect(page).toHaveURL(/\/listings/);
  });

  test("login with invalid credentials shows an error message", async ({ page }) => {
    await page.route(`${API_BASE}/auth/me`, (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) }),
    );

    await page.route(`${API_BASE}/auth/login`, (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Invalid credentials" }) }),
    );

    await page.goto("/login");

    await page.getByLabel("Email").fill("wrong@example.com");
    await page.getByLabel("Password").fill("bad-password");
    await page.getByRole("button", { name: "Sign In" }).click();

    // The page should display an error — the component renders "Invalid email or password"
    await expect(page.getByText("Invalid email or password")).toBeVisible();
  });

  test("logout redirects to /login", async ({ page }) => {
    await mockAuthenticated(page);

    await page.goto("/");

    // Wait for the dashboard to load (user's first name is shown)
    await expect(page.getByText("Welcome back, Test")).toBeVisible();

    // Click the "Log out" button in the Topbar
    await page.route(`${API_BASE}/auth/me`, (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) }),
    );

    await page.getByRole("button", { name: "Log out" }).click();

    await page.waitForURL("**/login");
    await expect(page).toHaveURL(/\/login/);
  });
});
