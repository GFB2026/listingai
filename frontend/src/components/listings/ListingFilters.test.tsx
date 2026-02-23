import { describe, it, expect, vi } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { ListingFilters } from "./ListingFilters";

const defaultFilters = {
  status: "",
  property_type: "",
  city: "",
  min_price: "",
  max_price: "",
  bedrooms: "",
  bathrooms: "",
  page: 1,
};

describe("ListingFilters", () => {
  it("renders all filter controls", () => {
    render(<ListingFilters filters={defaultFilters} onChange={() => {}} />);
    // 4 selects: status, property_type, bedrooms, bathrooms
    const selects = screen.getAllByRole("combobox");
    expect(selects).toHaveLength(4);
    // 3 text/number inputs: city, min_price, max_price
    expect(screen.getByPlaceholderText("Filter by city...")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Min price")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Max price")).toBeInTheDocument();
  });

  it("calls onChange with updated filter and resets page to 1", async () => {
    const onChange = vi.fn();
    render(<ListingFilters filters={defaultFilters} onChange={onChange} />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText("Filter by city..."), "Miami");
    // onChange should have been called for each keystroke
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.page).toBe(1);
  });

  it("shows Clear filters button when a filter is active", () => {
    render(
      <ListingFilters
        filters={{ ...defaultFilters, status: "active" }}
        onChange={() => {}}
      />
    );
    expect(screen.getByText("Clear filters")).toBeInTheDocument();
  });

  it("hides Clear filters when no filter is active", () => {
    render(<ListingFilters filters={defaultFilters} onChange={() => {}} />);
    expect(screen.queryByText("Clear filters")).not.toBeInTheDocument();
  });

  it("resets all filters on Clear click", async () => {
    const onChange = vi.fn();
    render(
      <ListingFilters
        filters={{ ...defaultFilters, status: "active", city: "Miami" }}
        onChange={onChange}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Clear filters"));
    expect(onChange).toHaveBeenCalledWith(defaultFilters);
  });
});
