import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, userEvent, waitFor } from "@/__tests__/test-utils";
import { ExportMenu } from "./ExportMenu";
import { useToastStore } from "@/hooks/useToast";

// Mock the api module to avoid MSW blob/stream issues
vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

import api from "@/lib/api";
const mockGet = vi.mocked(api.get);

describe("ExportMenu", () => {
  beforeEach(() => {
    useToastStore.setState({ toasts: [] });
    mockGet.mockReset();
  });

  it("renders export button", () => {
    render(<ExportMenu contentId="c1" />);
    expect(screen.getByText("Export")).toBeInTheDocument();
  });

  it("shows format options on click", async () => {
    render(<ExportMenu contentId="c1" />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Export"));
    expect(screen.getByText("Plain Text (.txt)")).toBeInTheDocument();
    expect(screen.getByText("HTML (.html)")).toBeInTheDocument();
    expect(screen.getByText("Word (.docx)")).toBeInTheDocument();
    expect(screen.getByText("PDF (.pdf)")).toBeInTheDocument();
  });

  it("closes dropdown on overlay click", async () => {
    render(<ExportMenu contentId="c1" />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Export"));
    expect(screen.getByText("Plain Text (.txt)")).toBeInTheDocument();

    // Click the overlay (fixed inset-0 div)
    const overlay = document.querySelector(".fixed.inset-0") as HTMLElement;
    await user.click(overlay);
    expect(screen.queryByText("Plain Text (.txt)")).not.toBeInTheDocument();
  });

  it("shows error toast on export failure", async () => {
    mockGet.mockRejectedValueOnce(new Error("Export failed"));

    render(<ExportMenu contentId="c1" />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Export"));
    await user.click(screen.getByText("Plain Text (.txt)"));

    await waitFor(() => {
      const toasts = useToastStore.getState().toasts;
      expect(toasts.some((t) => t.variant === "error")).toBe(true);
    });
  });
});
