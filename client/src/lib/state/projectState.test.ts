import { describe, it, expect, beforeEach } from "vitest";
import {
  projectView,
  setProject,
  setActiveDataset,
  clearProject,
} from "./projectState.svelte";
import { datasetView } from "./datasetState.svelte";
import type { Dataset, ProjectDetail } from "$lib/types";

function makeDataset(overrides?: Partial<Dataset>): Dataset {
  return {
    id: "d1",
    name: "SSP1",
    description: null,
    variables: [
      {
        name: "T2",
        vmin: 250,
        vmax: 310,
        units: "K",
        long_name: null,
        times: null,
        colormap: null,
      },
    ],
    ...overrides,
  };
}

function makeProject(overrides?: Partial<ProjectDetail>): ProjectDetail {
  return {
    id: "p1",
    title: "Tokyo Heat",
    description: "desc",
    datasets: [
      makeDataset({ id: "d1", name: "SSP1" }),
      makeDataset({ id: "d2", name: "SSP5" }),
    ],
    background_layers: [],
    ...overrides,
  };
}

describe("projectState", () => {
  beforeEach(() => {
    clearProject();
  });

  describe("setProject", () => {
    it("sets the active project", () => {
      setProject(makeProject());
      expect(projectView.project?.id).toBe("p1");
      expect(projectView.project?.title).toBe("Tokyo Heat");
    });

    it("auto-selects the first dataset", () => {
      setProject(makeProject());
      expect(projectView.activeDatasetId).toBe("d1");
      expect(datasetView.dataset?.id).toBe("d1");
    });

    it("exposes datasets from the active project", () => {
      setProject(makeProject());
      expect(projectView.datasets).toHaveLength(2);
      expect(projectView.datasets[0].id).toBe("d1");
    });

    it("replaces the previously active project", () => {
      setProject(makeProject());
      setProject(makeProject({ id: "p2", title: "Osaka Heat" }));
      expect(projectView.project?.id).toBe("p2");
      expect(projectView.activeDatasetId).toBe("d1");
    });
  });

  describe("setActiveDataset", () => {
    beforeEach(() => {
      setProject(makeProject());
    });

    it("switches the active dataset", () => {
      setActiveDataset("d2");
      expect(projectView.activeDatasetId).toBe("d2");
      expect(datasetView.dataset?.id).toBe("d2");
    });

    it("is a no-op for an unknown dataset id", () => {
      setActiveDataset("unknown");
      expect(projectView.activeDatasetId).toBe("d1");
      expect(datasetView.dataset?.id).toBe("d1");
    });
  });

  describe("clearProject", () => {
    it("clears project, activeDatasetId, and dataset state", () => {
      setProject(makeProject());
      clearProject();
      expect(projectView.project).toBeNull();
      expect(projectView.activeDatasetId).toBeNull();
      expect(datasetView.dataset).toBeNull();
    });

    it("returns empty datasets array when no project is set", () => {
      expect(projectView.datasets).toEqual([]);
    });
  });
});
