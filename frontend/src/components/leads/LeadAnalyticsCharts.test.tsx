import { describe, it, expect } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { LeadAnalyticsCharts } from "./LeadAnalyticsCharts";

const baseSummary = {
  total_leads: 10,
  by_status: { new: 4, contacted: 3, showing: 2, closed: 1 },
  by_source: { google: 5, facebook: 3, direct: 2 },
  by_agent: [
    { agent_name: "Jane Agent", agent_id: "a1", count: 6 },
    { agent_name: "Bob Agent", agent_id: "a2", count: 4 },
  ],
  total_closed_value: 750000,
};

const baseFunnel = {
  funnel: [
    { status: "new", count: 4, percentage: 40 },
    { status: "contacted", count: 3, percentage: 30 },
    { status: "showing", count: 2, percentage: 20 },
    { status: "under_contract", count: 0, percentage: 0 },
    { status: "closed", count: 1, percentage: 10 },
    { status: "lost", count: 0, percentage: 0 },
  ],
  total: 10,
};

describe("LeadAnalyticsCharts", () => {
  it("renders total closed revenue", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    expect(screen.getByText("$750,000")).toBeInTheDocument();
  });

  it("renders closed deal count", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    expect(screen.getByText(/1 closed deals/)).toBeInTheDocument();
  });

  it("renders source entries sorted by count", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    expect(screen.getByText("google")).toBeInTheDocument();
    expect(screen.getByText("facebook")).toBeInTheDocument();
    expect(screen.getByText("direct")).toBeInTheDocument();
  });

  it("renders source percentages", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    // google: 5/10 = 50%
    expect(screen.getByText("5 (50%)")).toBeInTheDocument();
  });

  it("renders funnel stages", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(screen.getByText("Contacted")).toBeInTheDocument();
    expect(screen.getByText("Under Contract")).toBeInTheDocument();
  });

  it("renders funnel percentages", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
  });

  it("renders agent leaderboard", () => {
    render(<LeadAnalyticsCharts summary={baseSummary} funnel={baseFunnel} />);
    expect(screen.getByText("Jane Agent")).toBeInTheDocument();
    expect(screen.getByText("6 leads")).toBeInTheDocument();
    expect(screen.getByText("Bob Agent")).toBeInTheDocument();
    expect(screen.getByText("4 leads")).toBeInTheDocument();
  });

  it("shows empty states when no data", () => {
    const emptySummary = {
      ...baseSummary,
      by_source: {},
      by_agent: [],
    };
    const emptyFunnel = { funnel: [], total: 0 };

    render(
      <LeadAnalyticsCharts summary={emptySummary} funnel={emptyFunnel} />
    );
    expect(screen.getByText("No source data")).toBeInTheDocument();
    expect(screen.getByText("No funnel data")).toBeInTheDocument();
    expect(screen.getByText("No agent data")).toBeInTheDocument();
  });

  it("renders singular 'lead' for count of 1", () => {
    const summary = {
      ...baseSummary,
      by_agent: [{ agent_name: "Solo", agent_id: "a1", count: 1 }],
    };
    render(<LeadAnalyticsCharts summary={summary} funnel={baseFunnel} />);
    expect(screen.getByText("1 lead")).toBeInTheDocument();
  });
});
