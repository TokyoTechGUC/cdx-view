const DEFAULT_OPACITY = 0.7;

interface MapState {
  opacity: number;
}

const state = $state<MapState>({
  opacity: DEFAULT_OPACITY,
});

export const mapView = {
  get opacity(): number {
    return state.opacity;
  },
};

export function setOpacity(value: number) {
  state.opacity = Math.max(0, Math.min(1, value));
}
