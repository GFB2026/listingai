import { describe, it, expect } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { PropertyHero } from "./PropertyHero";

const baseListing = {
  address_full: "100 Ocean Blvd, Fort Lauderdale, FL 33308",
  price: 1500000,
  bedrooms: 3,
  bathrooms: 2,
  sqft: 2200,
  year_built: 2015,
  description_original: "Beautiful oceanfront condo with panoramic views.",
  features: ["Pool", "Ocean View", "Balcony"],
  photos: [{ url: "https://example.com/photo1.jpg" }],
  property_type: "condo",
};

describe("PropertyHero", () => {
  it("renders hero photo", () => {
    render(<PropertyHero listing={baseListing} />);
    const img = screen.getByAltText(baseListing.address_full);
    expect(img).toHaveAttribute("src", "https://example.com/photo1.jpg");
  });

  it("renders placeholder when no photos", () => {
    render(<PropertyHero listing={{ ...baseListing, photos: null }} />);
    expect(screen.getByText("No Photo Available")).toBeInTheDocument();
  });

  it("renders formatted price", () => {
    render(<PropertyHero listing={baseListing} />);
    expect(screen.getByText("$1,500,000")).toBeInTheDocument();
  });

  it("renders 'Price Upon Request' when price is null", () => {
    render(<PropertyHero listing={{ ...baseListing, price: null }} />);
    expect(screen.getByText("Price Upon Request")).toBeInTheDocument();
  });

  it("renders address", () => {
    render(<PropertyHero listing={baseListing} />);
    expect(screen.getByText(baseListing.address_full)).toBeInTheDocument();
  });

  it("renders property type badge", () => {
    render(<PropertyHero listing={baseListing} />);
    expect(screen.getByText("condo")).toBeInTheDocument();
  });

  it("hides property type when null", () => {
    render(
      <PropertyHero listing={{ ...baseListing, property_type: null }} />
    );
    expect(screen.queryByText("condo")).not.toBeInTheDocument();
  });

  it("renders stat values", () => {
    render(<PropertyHero listing={baseListing} />);
    expect(screen.getByText("3")).toBeInTheDocument(); // beds
    expect(screen.getByText("2")).toBeInTheDocument(); // baths
    expect(screen.getByText("2,200")).toBeInTheDocument(); // sqft
    expect(screen.getByText("2015")).toBeInTheDocument(); // year
  });

  it("hides stats when null", () => {
    render(
      <PropertyHero
        listing={{
          ...baseListing,
          bedrooms: null,
          bathrooms: null,
          sqft: null,
          year_built: null,
        }}
      />
    );
    expect(screen.queryByText("Beds")).not.toBeInTheDocument();
    expect(screen.queryByText("Baths")).not.toBeInTheDocument();
  });

  it("renders description", () => {
    render(<PropertyHero listing={baseListing} />);
    expect(
      screen.getByText("Beautiful oceanfront condo with panoramic views.")
    ).toBeInTheDocument();
  });

  it("renders features list", () => {
    render(<PropertyHero listing={baseListing} />);
    expect(screen.getByText("Pool")).toBeInTheDocument();
    expect(screen.getByText("Ocean View")).toBeInTheDocument();
    expect(screen.getByText("Balcony")).toBeInTheDocument();
  });
});
