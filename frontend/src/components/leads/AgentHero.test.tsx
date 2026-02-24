import { describe, it, expect } from "vitest";
import { render, screen } from "@/__tests__/test-utils";
import { AgentHero } from "./AgentHero";

const baseProps = {
  name: "Jane Doe",
  headline: "Your Dream Home Awaits",
  bio: "Top-producing agent with 10 years of experience.",
  photoUrl: "https://example.com/photo.jpg",
  phone: "555-0100",
  email: "jane@realty.com",
  brokerageName: "Galt Ocean Realty",
};

describe("AgentHero", () => {
  it("renders agent name", () => {
    render(<AgentHero {...baseProps} />);
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("renders photo when photoUrl provided", () => {
    render(<AgentHero {...baseProps} />);
    const img = screen.getByAltText("Jane Doe");
    expect(img).toHaveAttribute("src", "https://example.com/photo.jpg");
  });

  it("renders initials when no photo", () => {
    render(<AgentHero {...baseProps} photoUrl={null} />);
    expect(screen.getByText("JD")).toBeInTheDocument();
  });

  it("renders headline", () => {
    render(<AgentHero {...baseProps} />);
    expect(screen.getByText("Your Dream Home Awaits")).toBeInTheDocument();
  });

  it("renders bio in full mode", () => {
    render(<AgentHero {...baseProps} />);
    expect(
      screen.getByText("Top-producing agent with 10 years of experience.")
    ).toBeInTheDocument();
  });

  it("hides bio in compact mode", () => {
    render(<AgentHero {...baseProps} compact />);
    expect(
      screen.queryByText("Top-producing agent with 10 years of experience.")
    ).not.toBeInTheDocument();
  });

  it("renders brokerage name", () => {
    render(<AgentHero {...baseProps} />);
    expect(screen.getByText("Galt Ocean Realty")).toBeInTheDocument();
  });

  it("renders phone link", () => {
    render(<AgentHero {...baseProps} />);
    const link = screen.getByText("555-0100");
    expect(link.closest("a")).toHaveAttribute("href", "tel:555-0100");
  });

  it("renders email link", () => {
    render(<AgentHero {...baseProps} />);
    const link = screen.getByText("Email");
    expect(link.closest("a")).toHaveAttribute("href", "mailto:jane@realty.com");
  });

  it("hides contact section when no phone or email", () => {
    render(<AgentHero {...baseProps} phone={null} email={null} />);
    expect(screen.queryByText("Email")).not.toBeInTheDocument();
    expect(screen.queryByText("555-0100")).not.toBeInTheDocument();
  });

  it("hides headline when null", () => {
    render(<AgentHero {...baseProps} headline={null} />);
    expect(
      screen.queryByText("Your Dream Home Awaits")
    ).not.toBeInTheDocument();
  });
});
