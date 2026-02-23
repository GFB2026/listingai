import { describe, it, expect } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { ListingCard } from "./ListingCard";

const baseListing = {
  id: "lst-1",
  address_full: "123 Ocean Blvd, Fort Lauderdale, FL 33308",
  price: 1250000,
  bedrooms: 4,
  bathrooms: 3,
  sqft: 2800,
  property_type: "Residential",
  status: "active",
  photos: [{ url: "https://example.com/photo.jpg" }],
};

describe("ListingCard", () => {
  it("renders formatted price", () => {
    render(<ListingCard listing={baseListing} />);
    expect(screen.getByText("$1,250,000")).toBeInTheDocument();
  });

  it("renders address", () => {
    render(<ListingCard listing={baseListing} />);
    expect(screen.getByText(baseListing.address_full)).toBeInTheDocument();
  });

  it("renders beds, baths, sqft", () => {
    render(<ListingCard listing={baseListing} />);
    expect(screen.getByText("4 bd")).toBeInTheDocument();
    expect(screen.getByText("3 ba")).toBeInTheDocument();
    expect(screen.getByText("2,800 sqft")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<ListingCard listing={baseListing} />);
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("shows No Photo when photos is empty", () => {
    render(<ListingCard listing={{ ...baseListing, photos: [] }} />);
    expect(screen.getByText("No Photo")).toBeInTheDocument();
  });

  it("shows No Photo when photos is null", () => {
    render(<ListingCard listing={{ ...baseListing, photos: null }} />);
    expect(screen.getByText("No Photo")).toBeInTheDocument();
  });

  it("links to listing detail page", () => {
    render(<ListingCard listing={baseListing} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/listings/lst-1");
  });
});
