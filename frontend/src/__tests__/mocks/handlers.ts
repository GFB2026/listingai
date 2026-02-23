import { http, HttpResponse } from "msw";

const BASE = "http://localhost:8000/api/v1";

// ---- Fixture data ----

export const mockUser = {
  id: "u1",
  email: "agent@example.com",
  full_name: "Jane Agent",
  role: "admin",
  tenant_id: "t1",
  is_active: true,
};

export const mockListing = {
  id: "lst-1",
  address_full: "123 Ocean Blvd, Fort Lauderdale, FL 33308",
  address_street: "123 Ocean Blvd",
  address_city: "Fort Lauderdale",
  address_state: "FL",
  address_zip: "33308",
  price: 1250000,
  bedrooms: 4,
  bathrooms: 3,
  sqft: 2800,
  lot_sqft: 5000,
  year_built: 2015,
  property_type: "Residential",
  status: "active",
  description_original: "Beautiful oceanfront property.",
  features: ["Pool", "Ocean View"],
  photos: [{ url: "https://example.com/photo1.jpg", caption: "Front" }],
  listing_agent_id: "agent-1",
  listing_agent_name: "Jane Agent",
  mls_listing_id: "MLS-12345",
  created_at: "2025-06-15T10:00:00Z",
};

export const mockContentItem = {
  id: "c1",
  content_type: "listing_description",
  tone: "luxury",
  body: "Stunning oceanfront estate with panoramic views.",
  metadata: { word_count: 8, character_count: 49, model: "claude-sonnet-4-5-20250514" },
  status: "completed",
  ai_model: "claude-sonnet-4-5-20250514",
  prompt_tokens: 500,
  completion_tokens: 200,
  generation_time_ms: 3200,
  version: 1,
  listing_id: "lst-1",
  created_at: "2025-06-15T12:00:00Z",
};

export const mockMlsConnection = {
  id: "mls-1",
  provider: "reso",
  name: "Florida MLS",
  base_url: "https://api.floridamls.com",
  sync_enabled: true,
  last_sync_at: "2025-06-15T08:00:00Z",
  created_at: "2025-01-01T00:00:00Z",
};

// ---- Handlers ----

export const handlers = [
  // Auth
  http.get(`${BASE}/auth/me`, () => HttpResponse.json(mockUser)),
  http.post(`${BASE}/auth/login`, () => HttpResponse.json({ message: "ok" })),
  http.post(`${BASE}/auth/register`, () => HttpResponse.json({ message: "ok" })),
  http.post(`${BASE}/auth/logout`, () => HttpResponse.json({ message: "ok" })),
  http.post(`${BASE}/auth/refresh`, () => HttpResponse.json({ message: "ok" })),

  // Listings
  http.get(`${BASE}/listings`, () =>
    HttpResponse.json({
      listings: [mockListing],
      total: 1,
      page: 1,
      page_size: 20,
    })
  ),
  http.get(`${BASE}/listings/:id`, () => HttpResponse.json(mockListing)),

  // Content
  http.get(`${BASE}/content`, () =>
    HttpResponse.json({
      content: [mockContentItem],
      total: 1,
      page: 1,
      page_size: 20,
    })
  ),
  http.get(`${BASE}/content/:id`, ({ params }) => {
    if (params.id === "c1") return HttpResponse.json(mockContentItem);
    return new HttpResponse(null, { status: 404 });
  }),
  http.post(`${BASE}/content/generate`, () =>
    HttpResponse.json([mockContentItem])
  ),
  http.get(`${BASE}/content/:id/export/:format`, () =>
    new HttpResponse(new Blob(["test"]), {
      headers: { "Content-Type": "application/octet-stream" },
    })
  ),

  // MLS Connections
  http.get(`${BASE}/mls-connections`, () =>
    HttpResponse.json({ connections: [mockMlsConnection] })
  ),
  http.get(`${BASE}/mls-connections/:id/status`, () =>
    HttpResponse.json({
      id: "mls-1",
      name: "Florida MLS",
      sync_enabled: true,
      last_sync_at: "2025-06-15T08:00:00Z",
      sync_watermark: "2025-06-15T08:00:00Z",
      listing_count: 42,
    })
  ),
  http.post(`${BASE}/mls-connections`, () => HttpResponse.json(mockMlsConnection)),
  http.post(`${BASE}/mls-connections/:id/test`, () =>
    HttpResponse.json({ success: true, message: "Connected", property_count: 42 })
  ),
  http.delete(`${BASE}/mls-connections/:id`, () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Brand profiles
  http.get(`${BASE}/brand-profiles`, () => HttpResponse.json([])),

  // Billing
  http.get(`${BASE}/billing/usage`, () =>
    HttpResponse.json({ credits_consumed: 5, credits_remaining: 95 })
  ),
];
