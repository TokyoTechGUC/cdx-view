import { describe, it, expect } from "vitest";
import { tileJsonUrl, backgroundTileJsonUrl } from "./tileServer";
import type { Dataset, VariableStats } from "$lib/types";

function makeVariable(overrides?: Partial<VariableStats>): VariableStats {
  return {
    name: "T2",
    vmin: 250,
    vmax: 310,
    units: "K",
    long_name: null,
    times: null,
    colormap: null,
    ...overrides,
  };
}

function makeDataset(overrides?: Partial<Dataset>): Dataset {
  return {
    id: "d1",
    name: "Test Dataset",
    description: null,
    format: "zarr",
    variables: [],
    ...overrides,
  };
}

describe("tileJsonUrl", () => {
  it("sends colormap_name and rescale for a named colormap", () => {
    const url = tileJsonUrl(
      makeDataset(),
      makeVariable(),
      0,
      "viridis",
      [250, 310],
    );
    const params = new URL(url).searchParams;
    expect(params.get("colormap_name")).toBe("viridis");
    expect(params.get("colormap")).toBeNull();
    expect(params.get("rescale")).toBe("250,310");
  });

  it("sends colormap (not colormap_name) and omits rescale for a JSON colormap", () => {
    const wbgt = "[[[-100,25],[51,153,255,255]],[[25,100],[204,0,0,255]]]";
    const url = tileJsonUrl(makeDataset(), makeVariable(), 0, wbgt, [250, 310]);
    const params = new URL(url).searchParams;
    expect(params.get("colormap")).toBe(wbgt);
    expect(params.get("colormap_name")).toBeNull();
    expect(params.get("rescale")).toBeNull();
  });

  it("still includes variable and bidx for non-cog datasets regardless of colormap type", () => {
    const wbgt = "[[[-100,25],[51,153,255,255]]]";
    const url = tileJsonUrl(
      makeDataset({ format: "zarr" }),
      makeVariable({ name: "WBGT" }),
      2,
      wbgt,
      [0, 40],
    );
    const params = new URL(url).searchParams;
    expect(params.get("variable")).toBe("WBGT");
    expect(params.get("bidx")).toBe("3");
  });

  it("omits variable and bidx for cog datasets", () => {
    const url = tileJsonUrl(
      makeDataset({ format: "cog" }),
      makeVariable(),
      0,
      "viridis",
      [250, 310],
    );
    const params = new URL(url).searchParams;
    expect(params.get("variable")).toBeNull();
    expect(params.get("bidx")).toBeNull();
  });
});

describe("backgroundTileJsonUrl", () => {
  it("defaults to Greys and the variable's own vmin/vmax when no rescale is given", () => {
    const url = backgroundTileJsonUrl(
      makeDataset(),
      makeVariable({ vmin: 0, vmax: 100 }),
    );
    const params = new URL(url).searchParams;
    expect(params.get("colormap_name")).toBe("greys");
    expect(params.get("rescale")).toBe("0,100");
  });

  it("omits rescale when the variable's own colormap is JSON", () => {
    const wbgt = "[[[-100,25],[51,153,255,255]]]";
    const url = backgroundTileJsonUrl(
      makeDataset(),
      makeVariable({ colormap: wbgt }),
    );
    const params = new URL(url).searchParams;
    expect(params.get("colormap")).toBe(wbgt);
    expect(params.get("rescale")).toBeNull();
  });
});
