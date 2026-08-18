import { PUBLIC_API_URL } from '$env/static/public';

export type RGBA = [number, number, number, number];
export type ColormapLUT = RGBA[];

const cache = new Map<string, ColormapLUT>();
const inFlight = new Map<string, Promise<ColormapLUT>>();

// Fetches a colormap's 256-entry RGBA lookup table from titiler and caches it
// in memory. Concurrent calls for the same name dedupe to a single request.
export async function fetchColormap(name: string): Promise<ColormapLUT> {
  const cached = cache.get(name);
  if (cached) return cached;

  const pending = inFlight.get(name);
  if (pending) return pending;

  const promise = (async () => {
    const res = await fetch(`${PUBLIC_API_URL}/colorMaps/${name}`);
    if (!res.ok) throw new Error(`Failed to fetch colormap ${name}: ${res.status}`);
    const json = (await res.json()) as Record<string, RGBA>;
    const lut: ColormapLUT = [];
    for (let i = 0; i < 256; i++) {
      const entry = json[String(i)];
      if (!entry) throw new Error(`Colormap ${name} is missing entry ${i}`);
      lut.push(entry);
    }
    cache.set(name, lut);
    return lut;
  })().finally(() => {
    inFlight.delete(name);
  });

  inFlight.set(name, promise);
  return promise;
}
