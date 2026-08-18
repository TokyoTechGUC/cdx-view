import type { Dataset, ProjectDetail } from '$lib/types';
import { clearDataset, selectDataset } from './datasetState.svelte';
import { clearBackgroundLayers, loadBackgroundLayers } from './backgroundLayerState.svelte';

interface ProjectState {
  project: ProjectDetail | null;
  activeDatasetId: string | null;
}

const state = $state<ProjectState>({
  project: null,
  activeDatasetId: null,
});

export const projectView = {
  get project(): ProjectDetail | null {
    return state.project;
  },
  get datasets(): Dataset[] {
    return state.project?.datasets ?? [];
  },
  get activeDatasetId(): string | null {
    return state.activeDatasetId;
  },
};

export function setProject(project: ProjectDetail) {
  state.project = project;
  loadBackgroundLayers(project.background_layers);
  const first = project.datasets[0] ?? null;
  state.activeDatasetId = first?.id ?? null;
  if (first) selectDataset(first);
}

export function setActiveDataset(datasetId: string) {
  const dataset = state.project?.datasets.find(d => d.id === datasetId);
  if (!dataset) return;
  state.activeDatasetId = datasetId;
  selectDataset(dataset);
}

export function clearProject() {
  state.project = null;
  state.activeDatasetId = null;
  clearDataset();
  clearBackgroundLayers();
}
