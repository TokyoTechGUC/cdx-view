import { describe, it, expect } from "vitest";
import { isJsonColormap, parseColormapSwatches } from "./colormapFormat";

describe("isJsonColormap", () => {
  it("returns false for named colormaps", () => {
    expect(isJsonColormap("viridis")).toBe(false);
    expect(isJsonColormap("rdylbu_r")).toBe(false);
  });

  it("returns true for JSON interval and discrete colormaps", () => {
    expect(isJsonColormap("[[[-100,25],[51,153,255,255]]]")).toBe(true);
    expect(isJsonColormap('{"1":[34,139,34,255]}')).toBe(true);
  });

  it("returns false for null or empty", () => {
    expect(isJsonColormap(null)).toBe(false);
    expect(isJsonColormap("")).toBe(false);
  });
});

describe("parseColormapSwatches", () => {
  it("returns null for a named colormap", () => {
    expect(parseColormapSwatches("viridis")).toBeNull();
  });

  it("returns null for malformed JSON", () => {
    expect(parseColormapSwatches("[[[")).toBeNull();
  });

  it("labels interval colormaps with open-ended first/last bands", () => {
    const wbgt =
      "[[[-100,25],[51,153,255,255]],[[25,28],[51,204,51,255]],[[28,31],[255,153,0,255]],[[31,100],[204,0,0,255]]]";
    const swatches = parseColormapSwatches(wbgt);
    expect(swatches).toEqual([
      { label: "< 25", color: [51, 153, 255, 255] },
      { label: "25–28", color: [51, 204, 51, 255] },
      { label: "28–31", color: [255, 153, 0, 255] },
      { label: "≥ 31", color: [204, 0, 0, 255] },
    ]);
  });

  it("labels a single-interval colormap as a closed range", () => {
    const swatches = parseColormapSwatches("[[[0,10],[255,0,0,255]]]");
    expect(swatches).toEqual([{ label: "0–10", color: [255, 0, 0, 255] }]);
  });

  it("parses discrete GDAL-style dicts sorted by numeric value", () => {
    const lc = '{"2":[70,130,180,255],"1":[34,139,34,255]}';
    const swatches = parseColormapSwatches(lc);
    expect(swatches).toEqual([
      { label: "1", color: [34, 139, 34, 255] },
      { label: "2", color: [70, 130, 180, 255] },
    ]);
  });
});
