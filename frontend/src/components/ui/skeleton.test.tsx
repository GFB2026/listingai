import { describe, it, expect } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { Skeleton, ListingCardSkeleton, DashboardSkeleton } from "./skeleton";

describe("Skeleton", () => {
  it("renders with default classes", () => {
    render(<Skeleton data-testid="skeleton" />);
    const el = screen.getByTestId("skeleton");
    expect(el.className).toContain("animate-pulse");
    expect(el.className).toContain("bg-gray-200");
  });

  it("merges custom className", () => {
    render(<Skeleton data-testid="skeleton" className="h-8 w-32" />);
    const el = screen.getByTestId("skeleton");
    expect(el.className).toContain("h-8");
    expect(el.className).toContain("w-32");
  });
});

describe("ListingCardSkeleton", () => {
  it("renders skeleton placeholders", () => {
    const { container } = render(<ListingCardSkeleton />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThanOrEqual(4);
  });
});

describe("DashboardSkeleton", () => {
  it("renders sidebar and content skeletons", () => {
    const { container } = render(<DashboardSkeleton />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    // Sidebar (logo + 6 items) + topbar (2) + title + 6 cards (each with 4 skeletons)
    expect(skeletons.length).toBeGreaterThanOrEqual(10);
  });
});
