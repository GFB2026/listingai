import { describe, it, expect, vi } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { ListingGrid } from "./ListingGrid";
import type { Listing } from "@/hooks/useListings";

const makeListing = (id: string): Listing => ({
  id,
  address_full: `${id} Main St`,
  address_street: `${id} Main St`,
  address_city: "Miami",
  address_state: "FL",
  address_zip: "33101",
  price: 500000,
  bedrooms: 3,
  bathrooms: 2,
  sqft: 1800,
  lot_sqft: null,
  year_built: null,
  property_type: "Residential",
  status: "active",
  description_original: null,
  features: [],
  photos: [],
  listing_agent_id: null,
  listing_agent_name: null,
  mls_listing_id: null,
  created_at: "2025-01-01T00:00:00Z",
});

describe("ListingGrid", () => {
  it("renders listing cards", () => {
    const listings = [makeListing("1"), makeListing("2")];
    render(
      <ListingGrid listings={listings} total={2} page={1} onPageChange={() => {}} />
    );
    expect(screen.getAllByRole("link")).toHaveLength(2);
  });

  it("shows empty state when no listings", () => {
    render(
      <ListingGrid listings={[]} total={0} page={1} onPageChange={() => {}} />
    );
    expect(screen.getByText(/no listings found/i)).toBeInTheDocument();
  });

  it("hides pagination when totalPages <= 1", () => {
    render(
      <ListingGrid
        listings={[makeListing("1")]}
        total={1}
        page={1}
        onPageChange={() => {}}
      />
    );
    expect(screen.queryByText("Previous")).not.toBeInTheDocument();
    expect(screen.queryByText("Next")).not.toBeInTheDocument();
  });

  it("shows pagination when totalPages > 1", () => {
    render(
      <ListingGrid
        listings={[makeListing("1")]}
        total={40}
        page={1}
        onPageChange={() => {}}
      />
    );
    expect(screen.getByText("Previous")).toBeInTheDocument();
    expect(screen.getByText("Next")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
  });

  it("calls onPageChange with next page", async () => {
    const onPageChange = vi.fn();
    render(
      <ListingGrid
        listings={[makeListing("1")]}
        total={40}
        page={1}
        onPageChange={onPageChange}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Next"));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("disables Previous on first page", () => {
    render(
      <ListingGrid
        listings={[makeListing("1")]}
        total={40}
        page={1}
        onPageChange={() => {}}
      />
    );
    expect(screen.getByText("Previous")).toBeDisabled();
  });
});
