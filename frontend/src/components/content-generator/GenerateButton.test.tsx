import { describe, it, expect, vi } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { GenerateButton } from "./GenerateButton";

describe("GenerateButton", () => {
  it("shows default text", () => {
    render(<GenerateButton onClick={() => {}} isLoading={false} />);
    expect(screen.getByText("Generate Content")).toBeInTheDocument();
  });

  it("shows loading text when generating", () => {
    render(<GenerateButton onClick={() => {}} isLoading={true} />);
    expect(screen.getByText("Generating...")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<GenerateButton onClick={onClick} isLoading={false} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("is disabled when loading", () => {
    render(<GenerateButton onClick={() => {}} isLoading={true} />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
