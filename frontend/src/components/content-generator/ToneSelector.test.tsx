import { describe, it, expect, vi } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { ToneSelector } from "./ToneSelector";
import { TONES } from "@/lib/utils";

describe("ToneSelector", () => {
  it("renders all tone buttons", () => {
    render(<ToneSelector value="" onChange={() => {}} />);
    for (const tone of TONES) {
      expect(screen.getByText(tone.label)).toBeInTheDocument();
    }
  });

  it("highlights selected tone", () => {
    render(<ToneSelector value="luxury" onChange={() => {}} />);
    const btn = screen.getByText("Luxury");
    expect(btn.className).toContain("bg-primary");
  });

  it("calls onChange with value on click", async () => {
    const onChange = vi.fn();
    render(<ToneSelector value="" onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Professional"));
    expect(onChange).toHaveBeenCalledWith("professional");
  });
});
