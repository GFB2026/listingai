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

const FAKE_LISTINGS = [
  {
    id: "lst_1",
    address_full: "100 Ocean Blvd, Fort Lauderdale, FL 33308",
    address_street: "100 Ocean Blvd",
    address_city: "Fort Lauderdale",
    address_state: "FL",
    address_zip: "33308",
    price: 1_250_000,
    bedrooms: 3,
    bathrooms: 2,
    sqft: 2_100,
    property_type: "condo",
    status: "active",
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: "lst_2",
    address_full: "200 Sunrise Ave, Fort Lauderdale, FL 33304",
    address_street: "200 Sunrise Ave",
    address_city: "Fort Lauderdale",
    address_state: "FL",
    address_zip: "33304",
    price: 875_000,
    bedrooms: 4,
    bathrooms: 3,
    sqft: 2_800,
    property_type: "single_family",
    status: "active",
    created_at: "2026-01-20T10:00:00Z",
  },
];

/**
 * Set up authenticated session + mock listing endpoints.
 */
async function setupAuthenticated(page: import("@playwright/test").Page) {
  await page.route(`${API_BASE}/auth/me`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_USER) }),
  );

  await page.route(`${API_BASE}/mls/connections**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ connections: [] }) }),
  );

  await page.route(`${API_BASE}/listings?**`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ listings: FAKE_LISTINGS, total: FAKE_LISTINGS.length }),
    }),
  );

  // Fallback for /listings without query params
  await page.route(`${API_BASE}/listings`, (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ listings: FAKE_LISTINGS, total: FAKE_LISTINGS.length }),
      });
    }
    return route.continue();
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe("Listings Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticated(page);
  });

  test("navigating to /listings shows the listings heading", async ({ page }) => {
    await page.goto("/listings");

    await expect(page.getByRole("heading", { name: "Listings" })).toBeVisible();
    // The subtitle shows total count
    await expect(page.getByText(`${FAKE_LISTINGS.length} listings synced from MLS`)).toBeVisible();
  });

  test("clicking 'Add Listing' reveals the create form", async ({ page }) => {
    await page.goto("/listings");

    // Click the Add Listing button
    await page.getByRole("button", { name: "Add Listing" }).click();

    // The form should now be visible
    await expect(page.getByText("Add New Listing")).toBeVisible();
    await expect(page.getByText("Address (full)")).toBeVisible();
  });

  test("creating a manual listing submits and closes the form", async ({ page }) => {
    const newListing = {
      id: "lst_new",
      address_full: "999 Test Dr, Miami, FL 33101",
      price: null,
      bedrooms: null,
      bathrooms: null,
      sqft: null,
      property_type: "",
      status: "active",
      created_at: "2026-02-27T10:00:00Z",
    };

    // Intercept the POST to create a listing
    await page.route(`${API_BASE}/listings`, (route) => {
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(newListing),
        });
      }
      // GET requests return updated list including the new listing
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          listings: [...FAKE_LISTINGS, newListing],
          total: FAKE_LISTINGS.length + 1,
        }),
      });
    });

    await page.goto("/listings");

    // Open the form
    await page.getByRole("button", { name: "Add Listing" }).click();
    await expect(page.getByText("Add New Listing")).toBeVisible();

    // Fill the required address field
    await page.getByPlaceholder("123 Main St, City, ST 12345").fill("999 Test Dr, Miami, FL 33101");

    // Submit
    await page.getByRole("button", { name: "Create Listing" }).click();

    // After success the form should close (the "Add New Listing" heading disappears)
    await expect(page.getByText("Add New Listing")).not.toBeVisible({ timeout: 10_000 });
  });
});
