import type { Dataset, VariableStats } from '$lib/types';

export interface BackgroundLayerEntry {
    dataset: Dataset;
    variable: VariableStats;
    visible: boolean;
    rescale: [number, number] | null;
}

const state = $state<{ layers: BackgroundLayerEntry[] }>({ layers: [] });

export const backgroundView = {
    get layers(): BackgroundLayerEntry[] {
        return state.layers;
    },
    get visibleLayers(): BackgroundLayerEntry[] {
        return state.layers.filter(e => e.visible);
    },
};

export function loadBackgroundLayers(datasets: Dataset[]) {
    state.layers = datasets.flatMap(dataset =>
        dataset.variables.map(variable => ({ dataset, variable, visible: false, rescale: null }))
    );
}

export function toggleBackgroundLayer(datasetId: string, variableName: string) {
    const entry = state.layers.find(
        e => e.dataset.id === datasetId && e.variable.name === variableName
    );
    if (entry) entry.visible = !entry.visible;
}

export function setBackgroundRescale(datasetId: string, variableName: string, vmin: number, vmax: number) {
    const entry = state.layers.find(
        e => e.dataset.id === datasetId && e.variable.name === variableName
    );
    if (entry) entry.rescale = [vmin, vmax];
}

export function clearBackgroundRescale(datasetId: string, variableName: string) {
    const entry = state.layers.find(
        e => e.dataset.id === datasetId && e.variable.name === variableName
    );
    if (entry) entry.rescale = null;
}

export function clearBackgroundLayers() {
    state.layers = [];
}
