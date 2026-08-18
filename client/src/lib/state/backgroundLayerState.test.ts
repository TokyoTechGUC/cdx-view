import { describe, it, expect, beforeEach } from 'vitest';
import {
  backgroundView,
  loadBackgroundLayers,
  toggleBackgroundLayer,
  clearBackgroundLayers,
  setBackgroundRescale,
  clearBackgroundRescale,
} from './backgroundLayerState.svelte';
import type { Dataset } from '$lib/types';

function makeDataset(overrides?: Partial<Dataset>): Dataset {
  return {
    id: 'bg1',
    name: 'Population 2050',
    description: null,
    format: 'cog',
    variables: [
      { name: 'pop', vmin: 0, vmax: 5000, units: 'persons/km²', long_name: 'Population density', times: null, colormap: 'plasma' },
    ],
    ...overrides,
  };
}

describe('backgroundLayerState', () => {
  beforeEach(() => {
    clearBackgroundLayers();
  });

  describe('loadBackgroundLayers', () => {
    it('initialises one entry per variable across all datasets', () => {
      const ds1 = makeDataset({ id: 'bg1', variables: [
        { name: 'pop', vmin: 0, vmax: 5000, units: null, long_name: null, times: null, colormap: null },
      ]});
      const ds2 = makeDataset({ id: 'bg2', variables: [
        { name: 'lc', vmin: 0, vmax: 10, units: null, long_name: null, times: null, colormap: null },
        { name: 'lc2', vmin: 0, vmax: 10, units: null, long_name: null, times: null, colormap: null },
      ]});
      loadBackgroundLayers([ds1, ds2]);
      expect(backgroundView.layers).toHaveLength(3);
    });

    it('sets all entries to invisible by default', () => {
      loadBackgroundLayers([makeDataset()]);
      expect(backgroundView.layers.every(e => !e.visible)).toBe(true);
    });

    it('replaces any previously loaded layers', () => {
      loadBackgroundLayers([makeDataset({ id: 'bg1' })]);
      loadBackgroundLayers([makeDataset({ id: 'bg2' })]);
      expect(backgroundView.layers).toHaveLength(1);
      expect(backgroundView.layers[0].dataset.id).toBe('bg2');
    });

    it('results in an empty list when given an empty array', () => {
      loadBackgroundLayers([makeDataset()]);
      loadBackgroundLayers([]);
      expect(backgroundView.layers).toHaveLength(0);
    });
  });

  describe('toggleBackgroundLayer', () => {
    beforeEach(() => {
      loadBackgroundLayers([makeDataset()]);
    });

    it('makes a hidden layer visible', () => {
      toggleBackgroundLayer('bg1', 'pop');
      expect(backgroundView.layers[0].visible).toBe(true);
    });

    it('hides a visible layer', () => {
      toggleBackgroundLayer('bg1', 'pop');
      toggleBackgroundLayer('bg1', 'pop');
      expect(backgroundView.layers[0].visible).toBe(false);
    });

    it('is a no-op for an unknown dataset id', () => {
      toggleBackgroundLayer('unknown', 'pop');
      expect(backgroundView.layers[0].visible).toBe(false);
    });

    it('is a no-op for an unknown variable name', () => {
      toggleBackgroundLayer('bg1', 'unknown');
      expect(backgroundView.layers[0].visible).toBe(false);
    });
  });

  describe('backgroundView.visibleLayers', () => {
    it('returns only visible entries', () => {
      const ds = makeDataset({ id: 'bg1', variables: [
        { name: 'pop', vmin: 0, vmax: 5000, units: null, long_name: null, times: null, colormap: null },
        { name: 'lc', vmin: 0, vmax: 10, units: null, long_name: null, times: null, colormap: null },
      ]});
      loadBackgroundLayers([ds]);
      toggleBackgroundLayer('bg1', 'pop');
      expect(backgroundView.visibleLayers).toHaveLength(1);
      expect(backgroundView.visibleLayers[0].variable.name).toBe('pop');
    });

    it('returns an empty list when nothing is visible', () => {
      loadBackgroundLayers([makeDataset()]);
      expect(backgroundView.visibleLayers).toHaveLength(0);
    });
  });

  describe('setBackgroundRescale', () => {
    beforeEach(() => {
      loadBackgroundLayers([makeDataset()]);
    });

    it('starts with rescale null after load', () => {
      expect(backgroundView.layers[0].rescale).toBeNull();
    });

    it('sets the rescale range for a known entry', () => {
      setBackgroundRescale('bg1', 'pop', 100, 2000);
      expect(backgroundView.layers[0].rescale).toEqual([100, 2000]);
    });

    it('overwrites a previously set rescale', () => {
      setBackgroundRescale('bg1', 'pop', 100, 2000);
      setBackgroundRescale('bg1', 'pop', 500, 3000);
      expect(backgroundView.layers[0].rescale).toEqual([500, 3000]);
    });

    it('is a no-op for an unknown dataset id', () => {
      setBackgroundRescale('unknown', 'pop', 100, 2000);
      expect(backgroundView.layers[0].rescale).toBeNull();
    });

    it('is a no-op for an unknown variable name', () => {
      setBackgroundRescale('bg1', 'unknown', 100, 2000);
      expect(backgroundView.layers[0].rescale).toBeNull();
    });
  });

  describe('clearBackgroundRescale', () => {
    beforeEach(() => {
      loadBackgroundLayers([makeDataset()]);
    });

    it('resets rescale to null after it was set', () => {
      setBackgroundRescale('bg1', 'pop', 100, 2000);
      clearBackgroundRescale('bg1', 'pop');
      expect(backgroundView.layers[0].rescale).toBeNull();
    });

    it('is a no-op when rescale is already null', () => {
      clearBackgroundRescale('bg1', 'pop');
      expect(backgroundView.layers[0].rescale).toBeNull();
    });

    it('is a no-op for an unknown dataset id', () => {
      setBackgroundRescale('bg1', 'pop', 100, 2000);
      clearBackgroundRescale('unknown', 'pop');
      expect(backgroundView.layers[0].rescale).toEqual([100, 2000]);
    });

    it('is a no-op for an unknown variable name', () => {
      setBackgroundRescale('bg1', 'pop', 100, 2000);
      clearBackgroundRescale('bg1', 'unknown');
      expect(backgroundView.layers[0].rescale).toEqual([100, 2000]);
    });
  });

  describe('clearBackgroundLayers', () => {
    it('empties the layer list', () => {
      loadBackgroundLayers([makeDataset()]);
      clearBackgroundLayers();
      expect(backgroundView.layers).toHaveLength(0);
    });

    it('empties visibleLayers too', () => {
      loadBackgroundLayers([makeDataset()]);
      toggleBackgroundLayer('bg1', 'pop');
      clearBackgroundLayers();
      expect(backgroundView.visibleLayers).toHaveLength(0);
    });
  });
});
