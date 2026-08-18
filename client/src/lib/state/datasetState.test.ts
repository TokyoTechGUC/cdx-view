import { describe, it, expect, beforeEach } from "vitest";
import {
  datasetView,
  selectDataset,
  selectVariable,
  setVariableTimes,
  setTimeIndex,
  stepTime,
  clearDataset,
  setVariableColormap,
  setVariableRescale,
  clearVariableRescale,
} from "./datasetState.svelte";
import type { Dataset } from "$lib/types";

function makeDataset(overrides?: Partial<Dataset>): Dataset {
  return {
    id: "d1",
    name: "Test Dataset",
    description: "desc",
    format: "zarr",
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
      {
        name: "U10",
        vmin: -10,
        vmax: 10,
        units: "m/s",
        times: null,
        colormap: null,
      },
    ],
    ...overrides,
  };
}

function makeEmptyDataset(overrides?: Partial<Dataset>): Dataset {
  return makeDataset({ ...overrides, variables: [] });
}

function withTimes(
  dataset: Dataset,
  variableName: string,
  times: string[],
): Dataset {
  const variable = dataset.variables.find((v) => v.name === variableName);
  if (variable) variable.times = times;
  return dataset;
}

describe("datasetState", () => {
  beforeEach(() => {
    clearDataset();
    selectDataset(makeDataset());
  });

  describe("selectDataset", () => {
    it("auto-selects the first variable", () => {
      expect(datasetView.dataset?.id).toBe("d1");
      expect(datasetView.selectedVariable?.name).toBe("T2");
    });

    it("leaves timeIndex null when the first variable has no fetched times", () => {
      expect(datasetView.timeIndex).toBeNull();
    });

    it("sets timeIndex to 0 when the first variable already has times", () => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2"]));
      expect(datasetView.selectedVariable?.name).toBe("T2");
      expect(datasetView.timeIndex).toBe(0);
    });

    it("handles a dataset with no variables", () => {
      selectDataset(makeEmptyDataset());
      expect(datasetView.dataset?.id).toBe("d1");
      expect(datasetView.selectedVariable).toBeNull();
      expect(datasetView.timeIndex).toBeNull();
    });
  });

  describe("selectDataset with a previously selected dataset", () => {
    it("keeps the selected variable when the new dataset has a variable with the same name", () => {
      selectVariable("U10");
      selectDataset(makeDataset({ id: "d2" }));
      expect(datasetView.dataset?.id).toBe("d2");
      expect(datasetView.selectedVariable?.name).toBe("U10");
    });

    it("falls back to the new dataset's first variable when there is no name match", () => {
      selectVariable("U10");
      selectDataset(
        makeDataset({
          id: "d2",
          variables: [
            {
              name: "PRCP",
              vmin: 0,
              vmax: 50,
              units: "mm",
              long_name: null,
              times: null,
              colormap: null,
            },
          ],
        }),
      );
      expect(datasetView.selectedVariable?.name).toBe("PRCP");
    });

    it("keeps the previous timeIndex when it is still in bounds for the matched variable's cached times", () => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
      setTimeIndex(2);
      selectDataset(
        withTimes(makeDataset({ id: "d2" }), "T2", ["s0", "s1", "s2", "s3"]),
      );
      expect(datasetView.selectedVariable?.name).toBe("T2");
      expect(datasetView.timeIndex).toBe(2);
    });

    it("resets timeIndex to 0 when it is out of bounds for the matched variable's cached times", () => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
      setTimeIndex(3);
      selectDataset(withTimes(makeDataset({ id: "d2" }), "T2", ["s0"]));
      expect(datasetView.timeIndex).toBe(0);
    });

    it("applies the previous timeIndex once times are fetched for a matched variable that wasn't cached yet", () => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
      setTimeIndex(2);
      selectDataset(makeDataset({ id: "d2" }));
      expect(datasetView.selectedVariable?.name).toBe("T2");
      expect(datasetView.timeIndex).toBeNull();
      setVariableTimes("T2", ["s0", "s1", "s2", "s3"]);
      expect(datasetView.timeIndex).toBe(2);
    });
  });

  describe("selectVariable", () => {
    it("selects an existing variable by name", () => {
      selectVariable("U10");
      expect(datasetView.selectedVariable?.name).toBe("U10");
    });

    it("is a no-op when no dataset is set", () => {
      clearDataset();
      selectVariable("T2");
      expect(datasetView.dataset).toBeNull();
      expect(datasetView.selectedVariable).toBeNull();
      expect(datasetView.timeIndex).toBeNull();
    });

    it("is a no-op for an unknown variable name", () => {
      selectVariable("NOPE");
      // Auto-selected T2 should stay.
      expect(datasetView.selectedVariable?.name).toBe("T2");
    });

    it("leaves timeIndex null when the variable has no fetched times", () => {
      selectVariable("U10");
      expect(datasetView.timeIndex).toBeNull();
    });

    it("sets timeIndex to 0 when the variable already has times", () => {
      selectDataset(withTimes(makeDataset(), "U10", ["t0", "t1", "t2"]));
      selectVariable("U10");
      expect(datasetView.timeIndex).toBe(0);
    });

    it("resets timeIndex when switching variables and the index is out of bounds", () => {
      const d = makeDataset();
      withTimes(d, "T2", ["t0", "t1", "t2"]);
      withTimes(d, "U10", ["t0"]);
      selectDataset(d);
      setTimeIndex(2);
      selectVariable("U10");
      expect(datasetView.timeIndex).toBe(0);
    });

    it("keeps timeIndex when switching variables and the index is still in bounds", () => {
      const d = makeDataset();
      withTimes(d, "T2", ["t0", "t1", "t2"]);
      withTimes(d, "U10", ["s0", "s1", "s2", "s3"]);
      selectDataset(d);
      setTimeIndex(2);
      selectVariable("U10");
      expect(datasetView.timeIndex).toBe(2);
    });

    it("applies the previous timeIndex once times are fetched for a variable that wasn't cached yet", () => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
      setTimeIndex(2);
      selectVariable("U10");
      expect(datasetView.timeIndex).toBeNull();
      setVariableTimes("U10", ["s0", "s1", "s2", "s3"]);
      expect(datasetView.timeIndex).toBe(2);
    });

    it("keeps the pending timeIndex through a second switch to another not-yet-fetched variable", () => {
      const d = makeDataset({
        variables: [
          {
            name: "T2",
            vmin: 250,
            vmax: 310,
            units: "K",
            long_name: null,
            times: ["t0", "t1", "t2", "t3"],
            colormap: null,
          },
          {
            name: "U10",
            vmin: -10,
            vmax: 10,
            units: "m/s",
            long_name: null,
            times: null,
            colormap: null,
          },
          {
            name: "V",
            vmin: -10,
            vmax: 10,
            units: "m/s",
            long_name: null,
            times: null,
            colormap: null,
          },
        ],
      });
      selectDataset(d);
      setTimeIndex(2);
      selectVariable("U10"); // not yet fetched -> pending = 2
      selectVariable("V"); // switch again before U10's times resolve
      setVariableTimes("V", ["s0", "s1", "s2", "s3"]);
      expect(datasetView.timeIndex).toBe(2);
    });

    it("falls back to default timeIndex once fetched times don't cover the pending index", () => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
      setTimeIndex(3);
      selectVariable("U10");
      setVariableTimes("U10", ["s0"]);
      expect(datasetView.timeIndex).toBe(0);
    });
  });

  describe("setVariableTimes", () => {
    it("populates times on the named variable", () => {
      setVariableTimes("U10", ["t0", "t1"]);
      const u10 = datasetView.dataset?.variables.find((v) => v.name === "U10");
      expect(u10?.times).toEqual(["t0", "t1"]);
    });

    it("auto-initializes timeIndex to 0 when populated for the selected variable", () => {
      selectVariable("T2");
      expect(datasetView.timeIndex).toBeNull();
      setVariableTimes("T2", ["t0", "t1", "t2"]);
      expect(datasetView.timeIndex).toBe(0);
    });

    it("does not touch timeIndex when populated for a non-selected variable", () => {
      selectVariable("T2");
      setVariableTimes("U10", ["t0", "t1"]);
      expect(datasetView.timeIndex).toBeNull();
    });

    it("is a no-op for an unknown variable name", () => {
      setVariableTimes("NOPE", ["t0"]);
      expect(datasetView.timeIndex).toBeNull();
    });
  });

  describe("setTimeIndex", () => {
    beforeEach(() => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
    });

    it("updates timeIndex when in range", () => {
      setTimeIndex(3);
      expect(datasetView.timeIndex).toBe(3);
    });

    it("rejects negative index", () => {
      setTimeIndex(-1);
      expect(datasetView.timeIndex).toBe(0);
    });

    it("rejects index >= times.length", () => {
      setTimeIndex(4);
      expect(datasetView.timeIndex).toBe(0);
    });

    it("is a no-op when the selected variable has no times", () => {
      selectVariable("U10");
      setTimeIndex(1);
      expect(datasetView.timeIndex).toBeNull();
    });

    it("is a no-op when no dataset is set", () => {
      clearDataset();
      setTimeIndex(1);
      expect(datasetView.timeIndex).toBeNull();
    });

    it("is a no-op when no variable is selected (empty dataset)", () => {
      selectDataset(makeEmptyDataset());
      setTimeIndex(1);
      expect(datasetView.selectedVariable).toBeNull();
      expect(datasetView.timeIndex).toBeNull();
    });
  });

  describe("setVariableColormap / selectedColormap", () => {
    it("defaults to viridis when nothing has been set", () => {
      expect(datasetView.selectedColormap).toBe("viridis");
    });

    it("reflects the colormap chosen for the selected variable", () => {
      setVariableColormap("T2", "rdylbu_r");
      expect(datasetView.selectedColormap).toBe("rdylbu_r");
    });

    it("falls back to default when the selected variable has no colormap set", () => {
      setVariableColormap("U10", "plasma");
      // T2 is still selected, has no colormap set.
      expect(datasetView.selectedColormap).toBe("viridis");
      selectVariable("U10");
      expect(datasetView.selectedColormap).toBe("plasma");
    });

    it("falls back to the variable's own colormap from the dataset before viridis", () => {
      selectDataset(
        makeDataset({
          id: "d3",
          variables: [
            {
              name: "T2",
              vmin: 250,
              vmax: 310,
              units: "K",
              long_name: null,
              times: null,
              colormap: "plasma",
            },
          ],
        }),
      );
      expect(datasetView.selectedColormap).toBe("plasma");
    });

    it("prefers a user-selected colormap over the variable's own default", () => {
      selectDataset(
        makeDataset({
          id: "d4",
          variables: [
            {
              name: "T2",
              vmin: 250,
              vmax: 310,
              units: "K",
              long_name: null,
              times: null,
              colormap: "plasma",
            },
          ],
        }),
      );
      setVariableColormap("T2", "rdylbu_r");
      expect(datasetView.selectedColormap).toBe("rdylbu_r");
    });

    it("is a no-op for an unknown variable name", () => {
      setVariableColormap("NOPE", "plasma");
      expect(datasetView.selectedColormap).toBe("viridis");
    });

    it("clears colormaps on selectDataset", () => {
      setVariableColormap("T2", "rdylbu_r");
      selectDataset(makeDataset({ id: "d2" }));
      expect(datasetView.selectedColormap).toBe("viridis");
    });

    it("clears colormaps on clearDataset", () => {
      setVariableColormap("T2", "rdylbu_r");
      clearDataset();
      expect(datasetView.selectedColormap).toBe("viridis");
    });
  });

  describe("setVariableRescale / clearVariableRescale / selectedRescale", () => {
    it("falls back to [vmin, vmax] when no override is set", () => {
      expect(datasetView.selectedRescale).toEqual([250, 310]);
    });

    it("returns null when no variable is selected", () => {
      clearDataset();
      expect(datasetView.selectedRescale).toBeNull();
    });

    it("reflects the override set for the selected variable", () => {
      setVariableRescale("T2", 270, 295);
      expect(datasetView.selectedRescale).toEqual([270, 295]);
    });

    it("preserves per-variable overrides when switching variables", () => {
      setVariableRescale("T2", 270, 295);
      setVariableRescale("U10", -5, 5);
      selectVariable("U10");
      expect(datasetView.selectedRescale).toEqual([-5, 5]);
      selectVariable("T2");
      expect(datasetView.selectedRescale).toEqual([270, 295]);
    });

    it("falls back to registered defaults for a variable with no override", () => {
      setVariableRescale("T2", 270, 295);
      selectVariable("U10");
      expect(datasetView.selectedRescale).toEqual([-10, 10]);
    });

    it("is a no-op for an unknown variable name", () => {
      setVariableRescale("NOPE", 0, 1);
      expect(datasetView.selectedRescale).toEqual([250, 310]);
    });

    it("clearVariableRescale restores registered defaults", () => {
      setVariableRescale("T2", 270, 295);
      clearVariableRescale("T2");
      expect(datasetView.selectedRescale).toEqual([250, 310]);
    });

    it("clearVariableRescale is a no-op for an unknown variable name", () => {
      setVariableRescale("T2", 270, 295);
      clearVariableRescale("NOPE");
      expect(datasetView.selectedRescale).toEqual([270, 295]);
    });

    it("clears rescale overrides on selectDataset", () => {
      setVariableRescale("T2", 270, 295);
      selectDataset(makeDataset({ id: "d2" }));
      expect(datasetView.selectedRescale).toEqual([250, 310]);
    });

    it("clears rescale overrides on clearDataset", () => {
      setVariableRescale("T2", 270, 295);
      clearDataset();
      expect(datasetView.selectedRescale).toBeNull();
    });
  });

  describe("stepTime", () => {
    beforeEach(() => {
      selectDataset(withTimes(makeDataset(), "T2", ["t0", "t1", "t2", "t3"]));
    });

    it("advances by a positive delta", () => {
      stepTime(1);
      expect(datasetView.timeIndex).toBe(1);
    });

    it("retreats by a negative delta", () => {
      stepTime(1);
      stepTime(-1);
      expect(datasetView.timeIndex).toBe(0);
    });

    it("is bounded by setTimeIndex range checks", () => {
      stepTime(-1);
      expect(datasetView.timeIndex).toBe(0);
    });

    it("is a no-op when timeIndex is null", () => {
      selectVariable("U10");
      stepTime(1);
      expect(datasetView.timeIndex).toBeNull();
    });
  });
});
