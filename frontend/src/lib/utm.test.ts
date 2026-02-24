import { describe, it, expect, beforeEach, vi } from "vitest";
import { captureUtmParams, getStoredUtm, getOrCreateSessionId } from "./utm";

describe("captureUtmParams", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("captures UTM params from URL and stores in sessionStorage", () => {
    Object.defineProperty(window, "location", {
      value: { search: "?utm_source=google&utm_medium=cpc&utm_campaign=spring" },
      writable: true,
    });

    const result = captureUtmParams();
    expect(result).toEqual({
      utm_source: "google",
      utm_medium: "cpc",
      utm_campaign: "spring",
    });

    const stored = JSON.parse(sessionStorage.getItem("gor_utm")!);
    expect(stored.utm_source).toBe("google");
  });

  it("returns stored UTM when no UTM params in URL", () => {
    sessionStorage.setItem(
      "gor_utm",
      JSON.stringify({ utm_source: "facebook" })
    );
    Object.defineProperty(window, "location", {
      value: { search: "" },
      writable: true,
    });

    const result = captureUtmParams();
    expect(result).toEqual({ utm_source: "facebook" });
  });

  it("captures all five UTM keys", () => {
    Object.defineProperty(window, "location", {
      value: {
        search:
          "?utm_source=fb&utm_medium=social&utm_campaign=launch&utm_content=ad1&utm_term=realty",
      },
      writable: true,
    });

    const result = captureUtmParams();
    expect(result).toEqual({
      utm_source: "fb",
      utm_medium: "social",
      utm_campaign: "launch",
      utm_content: "ad1",
      utm_term: "realty",
    });
  });

  it("returns empty object when no URL params and nothing stored", () => {
    Object.defineProperty(window, "location", {
      value: { search: "" },
      writable: true,
    });
    const result = captureUtmParams();
    expect(result).toEqual({});
  });
});

describe("getStoredUtm", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns stored UTM params", () => {
    sessionStorage.setItem(
      "gor_utm",
      JSON.stringify({ utm_source: "linkedin", utm_medium: "organic" })
    );
    const result = getStoredUtm();
    expect(result).toEqual({ utm_source: "linkedin", utm_medium: "organic" });
  });

  it("returns empty object when nothing stored", () => {
    expect(getStoredUtm()).toEqual({});
  });

  it("returns empty object on invalid JSON", () => {
    sessionStorage.setItem("gor_utm", "not-json{{{");
    expect(getStoredUtm()).toEqual({});
  });
});

describe("getOrCreateSessionId", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("creates a new session ID and stores it", () => {
    const id = getOrCreateSessionId();
    expect(id).toBeTruthy();
    expect(id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$/
    );
    expect(sessionStorage.getItem("gor_session")).toBe(id);
  });

  it("returns existing session ID on subsequent calls", () => {
    const first = getOrCreateSessionId();
    const second = getOrCreateSessionId();
    expect(first).toBe(second);
  });
});
