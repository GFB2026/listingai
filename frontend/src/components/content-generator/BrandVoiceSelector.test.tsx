import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@/__tests__/test-utils";
import { http, HttpResponse } from "msw";
import { server } from "@/__tests__/mocks/server";
import { BrandVoiceSelector } from "./BrandVoiceSelector";

const BASE = "http://localhost:8000/api/v1";

describe("BrandVoiceSelector", () => {
  it("renders select with default option", () => {
    render(<BrandVoiceSelector value={null} onChange={vi.fn()} />);
    expect(screen.getByLabelText("Select brand voice profile")).toBeInTheDocument();
    expect(screen.getByText("Use default (or none)")).toBeInTheDocument();
  });

  it("renders fetched brand profiles", async () => {
    server.use(
      http.get(`${BASE}/brand-profiles`, () =>
        HttpResponse.json([
          { id: "bp-1", name: "Luxury Coastal", is_default: true, voice_description: null },
          { id: "bp-2", name: "Modern Urban", is_default: false, voice_description: null },
        ])
      )
    );

    render(<BrandVoiceSelector value={null} onChange={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Luxury Coastal (Default)")).toBeInTheDocument();
      expect(screen.getByText("Modern Urban")).toBeInTheDocument();
    });
  });

  it("calls onChange when a profile is selected", async () => {
    server.use(
      http.get(`${BASE}/brand-profiles`, () =>
        HttpResponse.json([
          { id: "bp-1", name: "Luxury", is_default: false, voice_description: null },
        ])
      )
    );

    const onChange = vi.fn();
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();

    render(<BrandVoiceSelector value={null} onChange={onChange} />);

    await waitFor(() => {
      expect(screen.getByText("Luxury")).toBeInTheDocument();
    });

    await user.selectOptions(
      screen.getByLabelText("Select brand voice profile"),
      "bp-1"
    );
    expect(onChange).toHaveBeenCalledWith("bp-1");
  });

  it("calls onChange with null when default option selected", async () => {
    const onChange = vi.fn();
    const { userEvent } = await import("@/__tests__/test-utils");
    const user = userEvent.setup();

    render(<BrandVoiceSelector value="bp-1" onChange={onChange} />);

    await user.selectOptions(
      screen.getByLabelText("Select brand voice profile"),
      ""
    );
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
