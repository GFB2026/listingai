import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { LeadPipelineBoard } from "./LeadPipelineBoard";

const makeLead = (overrides: Record<string, unknown> = {}) => ({
  id: "lead-1",
  first_name: "John",
  last_name: "Doe",
  email: "john@example.com",
  phone: "555-0001",
  property_interest: null,
  pipeline_status: "new",
  utm_source: null,
  created_at: "2026-02-20T10:00:00Z",
  agent_name: null,
  ...overrides,
});

describe("LeadPipelineBoard", () => {
  it("renders all 6 pipeline columns", () => {
    render(
      <LeadPipelineBoard
        leads={[]}
        onStatusChange={vi.fn()}
        onLeadClick={vi.fn()}
      />
    );
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(screen.getByText("Contacted")).toBeInTheDocument();
    expect(screen.getByText("Showing")).toBeInTheDocument();
    expect(screen.getByText("Under Contract")).toBeInTheDocument();
    expect(screen.getByText("Closed")).toBeInTheDocument();
    expect(screen.getByText("Lost")).toBeInTheDocument();
  });

  it("shows 'No leads' for empty columns", () => {
    render(
      <LeadPipelineBoard
        leads={[]}
        onStatusChange={vi.fn()}
        onLeadClick={vi.fn()}
      />
    );
    const noLeads = screen.getAllByText("No leads");
    expect(noLeads).toHaveLength(6);
  });

  it("groups leads into correct columns", () => {
    const leads = [
      makeLead({ id: "l1", first_name: "Alice", last_name: null, pipeline_status: "new" }),
      makeLead({ id: "l2", first_name: "Bob", last_name: null, pipeline_status: "contacted" }),
      makeLead({ id: "l3", first_name: "Carol", last_name: null, pipeline_status: "new" }),
    ];
    render(
      <LeadPipelineBoard
        leads={leads}
        onStatusChange={vi.fn()}
        onLeadClick={vi.fn()}
      />
    );
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Carol")).toBeInTheDocument();
  });

  it("calls onLeadClick when a lead card is clicked", async () => {
    const onLeadClick = vi.fn();
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    const leads = [makeLead({ id: "l1", first_name: "Alice", last_name: null })];

    render(
      <LeadPipelineBoard
        leads={leads}
        onStatusChange={vi.fn()}
        onLeadClick={onLeadClick}
      />
    );
    await user.click(screen.getByText("Alice"));
    expect(onLeadClick).toHaveBeenCalledWith("l1");
  });

  it("renders status dropdown for each lead", () => {
    const leads = [makeLead()];
    render(
      <LeadPipelineBoard
        leads={leads}
        onStatusChange={vi.fn()}
        onLeadClick={vi.fn()}
      />
    );
    const selects = screen.getAllByRole("combobox");
    expect(selects.length).toBeGreaterThanOrEqual(1);
  });

  it("calls onStatusChange when dropdown value changes", async () => {
    const onStatusChange = vi.fn();
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    const leads = [makeLead({ id: "l1" })];

    render(
      <LeadPipelineBoard
        leads={leads}
        onStatusChange={onStatusChange}
        onLeadClick={vi.fn()}
      />
    );

    const select = screen.getAllByRole("combobox")[0];
    await user.selectOptions(select, "contacted");
    expect(onStatusChange).toHaveBeenCalledWith("l1", "contacted");
  });
});
