import { PUBLIC_API_URL } from "$env/static/public";
import { isJsonColormap } from "$lib/colormapFormat";
import type {
  Dataset,
  DatasetInfo,
  ProjectDetail,
  ProjectSummary,
  VariableStats,
} from "$lib/types";

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${PUBLIC_API_URL}/projects`);
  if (!res.ok) throw new Error(`Failed to fetch projects: ${res.status}`);
  return res.json();
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  const res = await fetch(`${PUBLIC_API_URL}/projects/${projectId}`);
  if (!res.ok) throw new Error(`Failed to fetch project: ${res.status}`);
  return res.json();
}

// TODO: deprecate once registry preprocesses times into VariableStats.
export async function getDatasetInfo(
  datasetId: string,
  variable: string,
): Promise<DatasetInfo> {
  const params = new URLSearchParams({
    dataset_id: datasetId,
    variable,
    show_times: "true",
  });
  const res = await fetch(`${PUBLIC_API_URL}/tiles/info?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch dataset info: ${res.status}`);
  return res.json();
}

export async function getPointValue(
  lon: number,
  lat: number,
  dataset: Dataset,
  variable: string,
  bidx: number,
  signal?: AbortSignal,
): Promise<number | null> {
  let url: string;
  if (dataset.format === "cog") {
    const params = new URLSearchParams({ dataset_id: dataset.id });
    url = `${PUBLIC_API_URL}/cog/point/${lon},${lat}?${params}`;
  } else {
    const params = new URLSearchParams({
      dataset_id: dataset.id,
      variable,
      bidx: String(bidx),
    });
    url = `${PUBLIC_API_URL}/tiles/point/${lon},${lat}?${params}`;
  }
  const res = await fetch(url, { signal });
  if (!res.ok) return null;
  const data = await res.json();
  return data.values?.[0] ?? null;
}

export function tileJsonUrl(
  dataset: Dataset,
  variable: VariableStats,
  timeIndex: number | null,
  colormap: string,
  rescale: [number, number],
): string {
  const params = new URLSearchParams({ dataset_id: dataset.id });
  const isJson = isJsonColormap(colormap);
  // Titiler applies `rescale` to the raw data before the colormap. A JSON
  // colormap's thresholds are written in raw data units, so rescaling first
  // would shift them against already-normalized values. Named colormaps are
  // designed for a normalized 0-255 range and need `rescale` to work at all.
  if (!isJson) {
    params.set("rescale", `${rescale[0]},${rescale[1]}`);
  }
  params.set(isJson ? "colormap" : "colormap_name", colormap);
  if (dataset.format === "cog") {
    return `${PUBLIC_API_URL}/cog/WebMercatorQuad/tilejson.json?${params}`;
  }
  params.set("variable", variable.name);
  params.set("bidx", String((timeIndex ?? 0) + 1));
  return `${PUBLIC_API_URL}/tiles/WebMercatorQuad/tilejson.json?${params}`;
}

export function backgroundTileJsonUrl(
  dataset: Dataset,
  variable: VariableStats,
  rescale?: [number, number],
): string {
  return tileJsonUrl(
    dataset,
    variable,
    null,
    variable.colormap ?? "greys",
    rescale ?? [variable.vmin, variable.vmax],
  );
}
