import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { Sidebar } from "./Sidebar";

// Mock the app store
const mockStore = { sidebarOpen: true, toggleSidebar: vi.fn(), setSidebarOpen: vi.fn() };
vi.mock("@/stores/app-store", () => ({
  useAppStore: () => mockStore,
}));

describe("Sidebar", () => {
  beforeEach(() => {
    mockStore.sidebarOpen = true;
  });

  it("renders all nav links", () => {
    render(<Sidebar />);
    const labels = ["Dashboard", "Listings", "Content", "Brand", "Settings", "MLS", "Billing"];
    for (const label of labels) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("highlights active route", () => {
    render(<Sidebar />);
    // "/" is the default pathname from our mock, so Dashboard should be active
    const dashboardLink = screen.getByText("Dashboard").closest("a");
    expect(dashboardLink?.className).toContain("text-primary");
  });

  it("shows full labels when sidebar is open", () => {
    render(<Sidebar />);
    expect(screen.getByText("ListingAI")).toBeInTheDocument();
  });

  it("hides labels when sidebar is collapsed", () => {
    mockStore.sidebarOpen = false;
    render(<Sidebar />);
    expect(screen.queryByText("ListingAI")).not.toBeInTheDocument();
    expect(screen.getByText("LA")).toBeInTheDocument();
  });
});
