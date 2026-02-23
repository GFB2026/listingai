import { describe, it, expect } from "vitest";
import { cn, formatPrice, formatDate, truncate, CONTENT_TYPES, TONES } from "./utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });

  it("resolves Tailwind conflicts (last wins)", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("handles empty / undefined inputs", () => {
    expect(cn("", undefined, null, "ok")).toBe("ok");
  });
});

describe("formatPrice", () => {
  it("formats a typical home price", () => {
    expect(formatPrice(1250000)).toBe("$1,250,000");
  });

  it("formats zero", () => {
    expect(formatPrice(0)).toBe("$0");
  });

  it("formats small values", () => {
    expect(formatPrice(99)).toBe("$99");
  });

  it("strips decimals", () => {
    expect(formatPrice(499999.99)).toBe("$500,000");
  });

  it("formats negative values", () => {
    expect(formatPrice(-5000)).toBe("-$5,000");
  });
});

describe("formatDate", () => {
  it("formats an ISO date string", () => {
    const result = formatDate("2025-06-15T10:00:00Z");
    expect(result).toContain("Jun");
    expect(result).toContain("15");
    expect(result).toContain("2025");
  });

  it("handles a date-only string", () => {
    // Date-only strings are interpreted as UTC; local formatting may shift the day
    const result = formatDate("2024-06-15");
    expect(result).toContain("2024");
    expect(result).toContain("Jun");
  });
});

describe("truncate", () => {
  it("returns short strings unchanged", () => {
    expect(truncate("hi", 10)).toBe("hi");
  });

  it("returns exact-length strings unchanged", () => {
    expect(truncate("hello", 5)).toBe("hello");
  });

  it("truncates long strings and adds ellipsis", () => {
    expect(truncate("hello world", 5)).toBe("hello...");
  });

  it("handles empty string", () => {
    expect(truncate("", 5)).toBe("");
  });
});

describe("CONTENT_TYPES", () => {
  it("has 10 entries", () => {
    expect(CONTENT_TYPES).toHaveLength(10);
  });

  it("includes listing_description", () => {
    expect(CONTENT_TYPES.find((ct) => ct.value === "listing_description")).toBeDefined();
  });

  it("includes all social platforms", () => {
    const socials = CONTENT_TYPES.filter((ct) => ct.value.startsWith("social_"));
    expect(socials).toHaveLength(4);
  });
});

describe("TONES", () => {
  it("has 5 entries", () => {
    expect(TONES).toHaveLength(5);
  });

  it("includes luxury and professional", () => {
    const values = TONES.map((t) => t.value);
    expect(values).toContain("luxury");
    expect(values).toContain("professional");
  });
});
