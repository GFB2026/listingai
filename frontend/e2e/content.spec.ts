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

const FAKE_CONTENT = [
  {
    id: "cnt_1",
    listing_id: "lst_1",
    content_type: "property_description",
    tone: "professional",
    body: "Stunning oceanfront condo with panoramic views of the Atlantic. This beautifully renovated unit features...",
    status: "draft",
    created_at: "2026-02-20T10:00:00Z",
  },
  {
    id: "cnt_2",
    listing_id: "lst_1",
    content_type: "social_post",
    tone: "casual",
    body: "Just listed! Check out this gorgeous 3BR/2BA condo right on the ocean in Fort Lauderdale...",
    status: "approved",
    created_at: "2026-02-21T10:00:00Z",
  },
  {
    id: "cnt_3",
    listing_id: "lst_2",
    content_type: "email_campaign",
    tone: "professional",
    body: "New on the market: a spacious single-family home in the heart of Fort Lauderdale offering...",
    status: "published",
    created_at: "2026-02-22T10:00:00Z",
  },
];

/**
 * Set up authenticated session + content endpoint mocks.
 */
async function setupAuthenticated(page: import("@playwright/test").Page) {
  await page.route(`${API_BASE}/auth/me`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_USER) }),
  );

  // Default content response (all items)
  await page.route(`${API_BASE}/content**`, (route) => {
    const url = new URL(route.request().url());
    const statusParam = url.searchParams.get("status");

    let filtered = FAKE_CONTENT;
    if (statusParam) {
      filtered = FAKE_CONTENT.filter((c) => c.status === statusParam);
    }

    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ content: filtered, total: filtered.length }),
    });
  });

  // Stub other endpoints the dashboard layout may call
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

  await page.route(`${API_BASE}/leads**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ leads: [], total: 0 }) }),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Content Library", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticated(page);
  });

  test("navigating to /content shows the Content Library heading and table", async ({ page }) => {
    await page.goto("/content");

    await expect(page.getByRole("heading", { name: "Content Library" })).toBeVisible();

    // Table headers should be present
    await expect(page.getByRole("columnheader", { name: "Type" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Tone" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
  });

  test("filtering content by status shows only matching items", async ({ page }) => {
    await page.goto("/content");

    // Initially all 3 items are shown
    await expect(page.getByRole("heading", { name: "Content Library" })).toBeVisible();

    // Select "Approved" from the status filter
    const statusSelect = page.locator("select").nth(1); // second <select> is status
    await statusSelect.selectOption("approved");

    // After filtering, only the approved item should appear
    await expect(page.getByText("social post")).toBeVisible();
    // The draft and published items should not be present
    await expect(page.getByText("property description")).not.toBeVisible();
    await expect(page.getByText("email campaign")).not.toBeVisible();
  });

  test("clicking View links to the listing content page", async ({ page }) => {
    await page.goto("/content");

    // The first content item has listing_id = lst_1, so its View link goes to /listings/lst_1/content
    const viewLinks = page.getByRole("link", { name: "View" });
    const firstViewLink = viewLinks.first();

    await expect(firstViewLink).toHaveAttribute("href", "/listings/lst_1/content");
  });
});
