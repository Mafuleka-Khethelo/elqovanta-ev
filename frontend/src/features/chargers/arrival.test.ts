import { describe, expect, it } from "vitest";
import { stationDateTimeInput } from "./arrival";

describe("station arrival input", () => {
  it("uses the station date across midnight rather than the device date", () => {
    expect(stationDateTimeInput("2026-10-29T23:15:00Z", "Africa/Johannesburg")).toBe("2026-10-30T01:15");
    expect(stationDateTimeInput("2026-10-29T06:15:00Z", "America/Los_Angeles")).toBe("2026-10-28T23:15");
  });
  it("follows station daylight saving changes and renders midnight as 00", () => {
    expect(stationDateTimeInput("2026-11-01T08:30:00Z", "America/Los_Angeles")).toBe("2026-11-01T01:30");
    expect(stationDateTimeInput("2026-11-01T09:30:00Z", "America/Los_Angeles")).toBe("2026-11-01T01:30");
    expect(stationDateTimeInput("2026-10-29T07:00:00Z", "America/Los_Angeles")).toBe("2026-10-29T00:00");
  });
});
