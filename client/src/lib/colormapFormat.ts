import type { RGBA } from "$lib/api/colormaps";

export interface ColormapSwatch {
  label: string;
  color: RGBA;
}

export function isJsonColormap(colormap: string | null): boolean {
  if (!colormap) return false;
  try {
    JSON.parse(colormap);
    return true;
  } catch {
    return false;
  }
}

function fmtNum(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

// Turns a JSON colormap string into legend swatches. Supports both formats
// titiler accepts: interval ranges ([[min, max], [r,g,b,a]][]) and discrete
// GDAL-style value maps ({"value": [r,g,b,a]}). Returns null for anything
// that isn't a JSON colormap (named colormaps, malformed JSON).
export function parseColormapSwatches(
  colormap: string,
): ColormapSwatch[] | null {
  try {
    const parsed: unknown = JSON.parse(colormap);

    if (Array.isArray(parsed)) {
      const entries = parsed as [[number, number], RGBA][];
      return entries.map(([[min, max], color], i) => {
        let label: string;
        if (entries.length === 1) label = `${fmtNum(min)}–${fmtNum(max)}`;
        else if (i === 0) label = `< ${fmtNum(max)}`;
        else if (i === entries.length - 1) label = `≥ ${fmtNum(min)}`;
        else label = `${fmtNum(min)}–${fmtNum(max)}`;
        return { label, color };
      });
    }

    if (parsed && typeof parsed === "object") {
      const entries = Object.entries(parsed as Record<string, RGBA>);
      return entries
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([value, color]) => ({ label: value, color }));
    }

    return null;
  } catch {
    return null;
  }
}
