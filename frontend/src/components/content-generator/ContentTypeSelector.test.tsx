import { describe, it, expect, vi } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { ContentTypeSelector } from "./ContentTypeSelector";
import { CONTENT_TYPES } from "@/lib/utils";

describe("ContentTypeSelector", () => {
  it("renders all content type buttons", () => {
    render(<ContentTypeSelector value="" onChange={() => {}} />);
    for (const ct of CONTENT_TYPES) {
      expect(screen.getByText(ct.label)).toBeInTheDocument();
    }
  });

  it("highlights selected type", () => {
    render(<ContentTypeSelector value="listing_description" onChange={() => {}} />);
    const btn = screen.getByText("Listing Description");
    expect(btn.className).toContain("border-primary");
  });

  it("calls onChange with value on click", async () => {
    const onChange = vi.fn();
    render(<ContentTypeSelector value="" onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Instagram Post"));
    expect(onChange).toHaveBeenCalledWith("social_instagram");
  });
});
