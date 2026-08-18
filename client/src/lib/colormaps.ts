// Curated colormap list shown in the side panel dropdown.
// Add/remove freely — names must match titiler's `/colorMaps` ids.
export const COLORMAPS = [
  // Sequential, perceptually uniform
  'viridis',
  'plasma',
  'magma',
  'cividis',
  'inferno',
  // Diverging (zero-centered: anomalies, deviations)
  'rdylbu_r',
  'coolwarm',
  'spectral_r',
  'rdbu_r',
  // Oceanographic / atmospheric (cmocean)
  'thermal',
  'balance',
  'haline',
  'dense',
  // Legacy (still requested in some workflows)
  'jet',
  'rainbow',
] as const;

export type Colormap = (typeof COLORMAPS)[number];
