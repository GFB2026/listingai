import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { LeadCard } from "./LeadCard";

const baseLead = {
  id: "lead-1",
  first_name: "John",
  last_name: "Doe",
  email: "john@example.com",
  phone: "555-0001",
  property_interest: "3BR condo near the beach in Fort Lauderdale with ocean views",
  utm_source: "google",
  created_at: "2026-02-20T10:00:00Z",
  agent_name: "Jane Agent",
};

describe("LeadCard", () => {
  it("renders full name", () => {
    render(<LeadCard lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("renders first name only when last name is null", () => {
    render(
      <LeadCard lead={{ ...baseLead, last_name: null }} onClick={vi.fn()} />
    );
    expect(screen.getByText("John")).toBeInTheDocument();
  });

  it("renders email", () => {
    render(<LeadCard lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
  });

  it("renders phone when no email", () => {
    render(
      <LeadCard lead={{ ...baseLead, email: null }} onClick={vi.fn()} />
    );
    expect(screen.getByText("555-0001")).toBeInTheDocument();
  });

  it("renders source badge for known source", () => {
    render(<LeadCard lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("G")).toBeInTheDocument();
  });

  it("renders truncated badge for unknown source", () => {
    render(
      <LeadCard
        lead={{ ...baseLead, utm_source: "newsletter" }}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByText("NEW")).toBeInTheDocument();
  });

  it("does not render badge when source is null", () => {
    render(
      <LeadCard
        lead={{ ...baseLead, utm_source: null }}
        onClick={vi.fn()}
      />
    );
    expect(screen.queryByText("G")).not.toBeInTheDocument();
  });

  it("truncates long property interest", () => {
    render(<LeadCard lead={baseLead} onClick={vi.fn()} />);
    // The text should be truncated to 60 chars
    const interest = screen.getByText(/3BR condo/);
    expect(interest.textContent!.length).toBeLessThanOrEqual(63); // 60 + "..."
  });

  it("renders agent name", () => {
    render(<LeadCard lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("Jane Agent")).toBeInTheDocument();
  });

  it("calls onClick with lead id", async () => {
    const onClick = vi.fn();
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    render(<LeadCard lead={baseLead} onClick={onClick} />);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledWith("lead-1");
  });
});
