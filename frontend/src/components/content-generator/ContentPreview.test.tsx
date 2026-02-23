import { describe, it, expect } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { ContentPreview } from "./ContentPreview";

const mockContent = [
  {
    id: "c1",
    content_type: "listing_description",
    tone: "luxury",
    body: "Stunning oceanfront estate with panoramic views.",
    metadata: { word_count: 8, character_count: 49, model: "claude-sonnet-4-5-20250514" },
    ai_model: "claude-sonnet-4-5-20250514",
    version: 1,
  },
  {
    id: "c2",
    content_type: "listing_description",
    tone: "luxury",
    body: "An exquisite oceanfront property offering unparalleled views.",
    metadata: { word_count: 9, character_count: 58, model: "claude-sonnet-4-5-20250514" },
    ai_model: "claude-sonnet-4-5-20250514",
    version: 1,
  },
];

describe("ContentPreview", () => {
  it("shows loading state", () => {
    render(<ContentPreview isLoading={true} />);
    expect(screen.getByText("Generating with Claude AI...")).toBeInTheDocument();
  });

  it("shows empty state when no content", () => {
    render(<ContentPreview isLoading={false} />);
    expect(
      screen.getByText("Select options and click Generate to create content")
    ).toBeInTheDocument();
  });

  it("renders body text", () => {
    render(
      <ContentPreview content={[mockContent[0]]} isLoading={false} />
    );
    expect(screen.getByText(mockContent[0].body)).toBeInTheDocument();
  });

  it("shows variant tabs when multiple variants exist", async () => {
    render(
      <ContentPreview content={mockContent} isLoading={false} />
    );
    expect(screen.getByText("Variant 1")).toBeInTheDocument();
    expect(screen.getByText("Variant 2")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByText("Variant 2"));
    expect(screen.getByText(mockContent[1].body)).toBeInTheDocument();
  });

  it("shows usage info when provided", () => {
    render(
      <ContentPreview
        content={[mockContent[0]]}
        usage={{ credits_consumed: 3, credits_remaining: 97 }}
        isLoading={false}
      />
    );
    expect(screen.getByText(/3 credits used/)).toBeInTheDocument();
    expect(screen.getByText(/97 remaining/)).toBeInTheDocument();
  });
});
