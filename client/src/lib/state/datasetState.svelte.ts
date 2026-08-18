import type { Dataset, VariableStats } from "$lib/types";

const DEFAULT_COLORMAP = "viridis";

interface DatasetState {
  dataset: Dataset | null;
  selectedVariableName: string | null;
  timeIndex: number | null;
  // Desired timeIndex carried over from a previous selection, held here until
  // the newly selected variable's times are fetched and it can be validated.
  pendingTimeIndex: number | null;
  variableColormaps: Record<string, string>;
  variableRescale: Record<string, [number, number]>;
}

const state = $state<DatasetState>({
  dataset: null,
  selectedVariableName: null,
  timeIndex: null,
  pendingTimeIndex: null,
  variableColormaps: {},
  variableRescale: {},
});

function findVariable(name: string | null): VariableStats | null {
  if (!state.dataset || !name) return null;
  return state.dataset.variables.find((v) => v.name === name) ?? null;
}

function defaultVariable(dataset: Dataset | null): VariableStats | null {
  return dataset?.variables[0] ?? null;
}

function defaultTimeIndex(variable: VariableStats | null): number | null {
  return variable?.times && variable.times.length > 0 ? 0 : null;
}

// Readonly view — the only way to read state outside this module.
// Getters preserve Svelte 5 reactivity on each access.
export const datasetView = {
  get dataset(): Dataset | null {
    return state.dataset;
  },
  get selectedVariable(): VariableStats | null {
    return findVariable(state.selectedVariableName);
  },
  get times(): string[] | null {
    return findVariable(state.selectedVariableName)?.times ?? null;
  },
  get timeIndex(): number | null {
    return state.timeIndex;
  },
  get selectedColormap(): string {
    const variable = findVariable(state.selectedVariableName);
    if (!variable) return DEFAULT_COLORMAP;
    return (
      state.variableColormaps[variable.name] ??
      variable.colormap ??
      DEFAULT_COLORMAP
    );
  },
  get selectedRescale(): [number, number] | null {
    const v = findVariable(state.selectedVariableName);
    if (!v) return null;
    return state.variableRescale[v.name] ?? [v.vmin, v.vmax];
  },
};

export function selectDataset(dataset: Dataset) {
  const previousVariableName = state.selectedVariableName;
  const previousTimeIndex = state.timeIndex ?? state.pendingTimeIndex;
  state.dataset = dataset;
  state.selectedVariableName = null;
  state.timeIndex = null;
  state.pendingTimeIndex = null;
  state.variableColormaps = {};
  state.variableRescale = {};
  const matched = previousVariableName
    ? dataset.variables.find((v) => v.name === previousVariableName)
    : null;
  const next = matched ?? defaultVariable(dataset);
  if (next) selectVariable(next.name);
  if (matched && previousTimeIndex !== null) {
    if (matched.times) {
      if (previousTimeIndex < matched.times.length) {
        state.timeIndex = previousTimeIndex;
      }
    } else {
      state.pendingTimeIndex = previousTimeIndex;
    }
  }
}

export function clearDataset() {
  state.dataset = null;
  state.selectedVariableName = null;
  state.timeIndex = null;
  state.pendingTimeIndex = null;
  state.variableColormaps = {};
  state.variableRescale = {};
}

export function selectVariable(name: string) {
  const variable = findVariable(name);
  if (!variable) return;
  const previousTimeIndex = state.timeIndex ?? state.pendingTimeIndex;
  state.selectedVariableName = name;
  if (variable.times) {
    state.timeIndex =
      previousTimeIndex !== null && previousTimeIndex < variable.times.length
        ? previousTimeIndex
        : defaultTimeIndex(variable);
    state.pendingTimeIndex = null;
  } else {
    state.timeIndex = null;
    state.pendingTimeIndex = previousTimeIndex;
  }
}

export function setVariableTimes(variableName: string, times: string[]) {
  const variable = findVariable(variableName);
  if (!variable) return;
  variable.times = times;
  if (state.selectedVariableName === variableName && state.timeIndex === null) {
    const pending = state.pendingTimeIndex;
    state.timeIndex =
      pending !== null && pending < times.length
        ? pending
        : defaultTimeIndex(variable);
    state.pendingTimeIndex = null;
  }
}

export function setTimeIndex(index: number) {
  const variable = findVariable(state.selectedVariableName);
  if (!variable?.times || variable.times.length === 0) return;
  if (index < 0 || index >= variable.times.length) return;
  state.timeIndex = index;
}

export function stepTime(delta: number) {
  if (state.timeIndex === null) return;
  setTimeIndex(state.timeIndex + delta);
}

export function setVariableColormap(variableName: string, colormap: string) {
  const variable = findVariable(variableName);
  if (!variable) return;
  state.variableColormaps[variableName] = colormap;
}

export function setVariableRescale(
  variableName: string,
  vmin: number,
  vmax: number,
) {
  const variable = findVariable(variableName);
  if (!variable) return;
  state.variableRescale[variableName] = [vmin, vmax];
}

export function clearVariableRescale(variableName: string) {
  const variable = findVariable(variableName);
  if (!variable) return;
  delete state.variableRescale[variableName];
}
