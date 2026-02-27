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
 * Set up authenticated session + stub every data endpoint the dashboard may
 * call so we can freely navigate without network errors.
 */
async function setupAuthenticated(page: import("@playwright/test").Page) {
  await page.route(`${API_BASE}/auth/me`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_USER) }),
  );

  await page.route(`${API_BASE}/billing/**`, (route) =>
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

  await page.route(`${API_BASE}/mls/**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ connections: [] }) }),
  );

  await page.route(`${API_BASE}/brand**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ profiles: [], total: 0 }) }),
  );

  await page.route(`${API_BASE}/email**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ campaigns: [], total: 0 }) }),
  );

  await page.route(`${API_BASE}/social**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ posts: [], total: 0 }) }),
  );

  await page.route(`${API_BASE}/settings**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) }),
  );

  await page.route(`${API_BASE}/users**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ users: [], total: 0 }) }),
  );

  await page.route(`${API_BASE}/agent-pages**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ pages: [], total: 0 }) }),
  );
}

// The nav items as defined in Sidebar.tsx
const NAV_ITEMS = [
  { label: "Dashboard", href: "/" },
  { label: "Listings", href: "/listings" },
  { label: "Content", href: "/content" },
  { label: "Leads", href: "/leads" },
  { label: "Analytics", href: "/leads/analytics" },
  { label: "Brand", href: "/brand" },
  { label: "Email", href: "/email" },
  { label: "Social", href: "/social" },
  { label: "Settings", href: "/settings" },
  { label: "MLS", href: "/settings/mls" },
  { label: "Agent Pages", href: "/settings/agent-pages" },
  { label: "Team", href: "/settings/users" },
  { label: "Billing", href: "/billing" },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("App Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticated(page);
  });

  test("sidebar displays all expected navigation items", async ({ page }) => {
    await page.goto("/");

    // Wait for the dashboard to render
    await expect(page.getByRole("heading", { name: /Welcome back/ })).toBeVisible();

    // Verify every nav item label is present in the sidebar
    for (const item of NAV_ITEMS) {
      await expect(page.getByRole("link", { name: item.label, exact: true })).toBeVisible();
    }
  });

  test("clicking each nav item navigates to the correct page", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Welcome back/ })).toBeVisible();

    // Test a representative subset to keep the test fast
    const sampled = [
      { label: "Listings", href: "/listings" },
      { label: "Content", href: "/content" },
      { label: "Leads", href: "/leads" },
      { label: "Brand", href: "/brand" },
      { label: "Billing", href: "/billing" },
    ];

    for (const item of sampled) {
      await page.getByRole("link", { name: item.label, exact: true }).click();
      await page.waitForURL(`**${item.href}`);
      await expect(page).toHaveURL(new RegExp(item.href.replace("/", "\\/")));
    }
  });

  test("sidebar collapse toggle hides nav labels and shows them again", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Welcome back/ })).toBeVisible();

    // Sidebar is open by default — labels should be visible
    await expect(page.getByRole("link", { name: "Listings", exact: true })).toContainText("Listings");

    // Click the toggle button (aria-label="Toggle sidebar")
    await page.getByLabel("Toggle sidebar").click();

    // After collapse the sidebar width shrinks and labels are hidden.
    // The links still exist but their text span is conditionally rendered.
    // The sidebar container should now have the narrow width class.
    const sidebar = page.locator("aside");
    await expect(sidebar).toHaveClass(/w-16/);

    // Toggle back open
    await page.getByLabel("Toggle sidebar").click();
    await expect(sidebar).toHaveClass(/w-56/);

    // Labels should be visible again
    await expect(page.getByRole("link", { name: "Listings", exact: true })).toContainText("Listings");
  });
});
