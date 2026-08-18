import { describe, it, expect } from "vitest";
import { formatTime } from "./formatTime";

describe("formatTime", () => {
  // --- naive datetimes (no timezone info) ---
  it("formats naive datetime with nanosecond precision", () => {
    expect(formatTime("2020-06-01T12:00:00.000000000")).toBe("2020-06-01 12:00");
  });

  it("formats naive datetime with microsecond precision", () => {
    expect(formatTime("2020-06-01T12:00:00.000000")).toBe("2020-06-01 12:00");
  });

  it("formats naive datetime with second precision", () => {
    expect(formatTime("2020-06-01T12:00:00")).toBe("2020-06-01 12:00");
  });

  it("formats naive datetime at midnight", () => {
    expect(formatTime("2020-01-01T00:00:00.000000000")).toBe("2020-01-01 00:00");
  });

  // --- UTC ---
  it("formats UTC datetime with Z suffix", () => {
    expect(formatTime("2020-06-01T12:00:00Z")).toBe("2020-06-01 12:00 UTC");
  });

  it("formats UTC datetime with Z and fractional seconds", () => {
    expect(formatTime("2020-06-01T03:00:00.000Z")).toBe("2020-06-01 03:00 UTC");
  });

  it("formats UTC datetime with nanosecond precision Z suffix", () => {
    expect(formatTime("2020-06-01T12:00:00.000000000Z")).toBe("2020-06-01 12:00 UTC");
  });

  // --- offset-aware ---
  it("formats datetime with positive offset", () => {
    expect(formatTime("2020-06-01T12:00:00+09:00")).toBe("2020-06-01 12:00 +09:00");
  });

  it("formats datetime with negative offset", () => {
    expect(formatTime("2020-06-01T12:00:00-05:00")).toBe("2020-06-01 12:00 -05:00");
  });

  it("formats datetime with zero offset", () => {
    expect(formatTime("2020-06-01T12:00:00+00:00")).toBe("2020-06-01 12:00 +00:00");
  });

  // --- fallback ---
  it("returns empty string for empty input", () => {
    expect(formatTime("")).toBe("");
  });

  it("returns string as-is for non-datetime values", () => {
    expect(formatTime("some_label")).toBe("some_label");
  });

  it("returns string as-is for date-only values", () => {
    expect(formatTime("2020-06-01")).toBe("2020-06-01");
  });
});
