import { describe, expect, it } from "vitest";
import { coordinateNote, formatDuration, statusLabel } from "./format";

describe("display helpers", () => {
  it("formats durations from whole seconds", () => {
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(59)).toBe("59s");
    expect(formatDuration(90)).toBe("1m 30s");
    expect(formatDuration(3661)).toBe("1h 1m 1s");
  });

  it("pairs status colours with words rather than colour alone", () => {
    expect(statusLabel("available")).toBe("Reported available");
    expect(statusLabel("unknown")).toBe("Not reported");
  });

  it("explains why a charger can be missing from the map", () => {
    expect(coordinateNote("inconsistent")).toMatch(/left off the map/);
    expect(coordinateNote("missing")).toMatch(/not mapped/);
  });
});
