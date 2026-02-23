import { describe, it, expect, vi } from "vitest";
import { render, screen, userEvent } from "@/__tests__/test-utils";
import { Topbar } from "./Topbar";

const mockLogout = vi.fn();
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u1", full_name: "Jane Agent", email: "jane@example.com", role: "admin" },
    logout: mockLogout,
  }),
}));

vi.mock("@/stores/app-store", () => ({
  useAppStore: () => ({
    toggleSidebar: vi.fn(),
  }),
}));

describe("Topbar", () => {
  it("displays user name", () => {
    render(<Topbar />);
    expect(screen.getByText("Jane Agent")).toBeInTheDocument();
  });

  it("shows logout button", () => {
    render(<Topbar />);
    expect(screen.getByText("Log out")).toBeInTheDocument();
  });

  it("calls logout on button click", async () => {
    mockLogout.mockResolvedValue(undefined);
    render(<Topbar />);
    const user = userEvent.setup();
    await user.click(screen.getByText("Log out"));
    expect(mockLogout).toHaveBeenCalled();
  });
});
