import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@/__tests__/test-utils";
import { LeadCaptureForm } from "./LeadCaptureForm";

// Mock public-api module
vi.mock("@/lib/public-api", () => ({
  default: {
    post: vi.fn(),
  },
}));

// Mock utm module
vi.mock("@/lib/utm", () => ({
  getStoredUtm: vi.fn(() => ({ utm_source: "google" })),
  getOrCreateSessionId: vi.fn(() => "session-123"),
}));

const defaultProps = {
  tenantSlug: "test-brokerage",
  agentSlug: "jane-agent",
};

describe("LeadCaptureForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form with all fields", () => {
    render(<LeadCaptureForm {...defaultProps} />);
    expect(screen.getByText("Get in Touch")).toBeInTheDocument();
    expect(screen.getByLabelText(/First Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Last Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Phone/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Message/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Send Message/ })).toBeInTheDocument();
  });

  it("shows validation error for empty first name", async () => {
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    render(<LeadCaptureForm {...defaultProps} />);
    await user.click(screen.getByRole("button", { name: /Send Message/ }));
    expect(screen.getByText("First name is required")).toBeInTheDocument();
  });

  it("shows validation error for invalid email", async () => {
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    render(<LeadCaptureForm {...defaultProps} />);

    await user.type(screen.getByLabelText(/First Name/), "John");
    await user.type(screen.getByLabelText(/Email/), "not-an-email");
    await user.click(screen.getByRole("button", { name: /Send Message/ }));

    expect(
      screen.getByText("Please enter a valid email address")
    ).toBeInTheDocument();
  });

  it("clears field error when user types", async () => {
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    render(<LeadCaptureForm {...defaultProps} />);

    // Trigger validation error
    await user.click(screen.getByRole("button", { name: /Send Message/ }));
    expect(screen.getByText("First name is required")).toBeInTheDocument();

    // Type to clear
    await user.type(screen.getByLabelText(/First Name/), "J");
    expect(
      screen.queryByText("First name is required")
    ).not.toBeInTheDocument();
  });

  it("submits form successfully and shows thank you", async () => {
    const publicApi = await import("@/lib/public-api");
    (publicApi.default.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {},
    });

    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();
    const onSuccess = vi.fn();

    render(<LeadCaptureForm {...defaultProps} onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText(/First Name/), "John");
    await user.type(screen.getByLabelText(/Email/), "john@example.com");
    await user.click(screen.getByRole("button", { name: /Send Message/ }));

    await waitFor(() => {
      expect(screen.getByText("Thank You!")).toBeInTheDocument();
    });
    expect(onSuccess).toHaveBeenCalled();
    expect(publicApi.default.post).toHaveBeenCalledWith(
      "/leads",
      expect.objectContaining({
        tenant_slug: "test-brokerage",
        agent_slug: "jane-agent",
        first_name: "John",
        email: "john@example.com",
        utm_source: "google",
        session_id: "session-123",
      })
    );
  });

  it("shows error message on submission failure", async () => {
    const publicApi = await import("@/lib/public-api");
    (publicApi.default.post as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network error")
    );

    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();

    render(<LeadCaptureForm {...defaultProps} />);

    await user.type(screen.getByLabelText(/First Name/), "John");
    await user.click(screen.getByRole("button", { name: /Send Message/ }));

    await waitFor(() => {
      expect(
        screen.getByText("Something went wrong. Please try again.")
      ).toBeInTheDocument();
    });
  });

  it("disables button while submitting", async () => {
    const publicApi = await import("@/lib/public-api");
    let resolvePost: (value: unknown) => void;
    (publicApi.default.post as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((resolve) => {
        resolvePost = resolve;
      })
    );

    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();

    render(<LeadCaptureForm {...defaultProps} />);
    await user.type(screen.getByLabelText(/First Name/), "John");
    await user.click(screen.getByRole("button", { name: /Send Message/ }));

    expect(screen.getByRole("button", { name: /Sending/ })).toBeDisabled();

    // Resolve to clean up
    resolvePost!({ data: {} });
    await waitFor(() => {
      expect(screen.getByText("Thank You!")).toBeInTheDocument();
    });
  });

  it("shows ThankYouMessage with agent name", async () => {
    const publicApi = await import("@/lib/public-api");
    (publicApi.default.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {},
    });

    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();

    render(
      <LeadCaptureForm {...defaultProps} agentName="Jane Agent" />
    );
    await user.type(screen.getByLabelText(/First Name/), "John");
    await user.click(screen.getByRole("button", { name: /Send Message/ }));

    await waitFor(() => {
      expect(
        screen.getByText("Jane Agent will be in touch with you shortly.")
      ).toBeInTheDocument();
    });
  });

  it("pre-fills property interest from prop", () => {
    render(
      <LeadCaptureForm
        {...defaultProps}
        propertyInterest="100 Ocean Blvd"
      />
    );
    const input = screen.getByLabelText(/Property of Interest/) as HTMLInputElement;
    expect(input.value).toBe("100 Ocean Blvd");
  });
});
