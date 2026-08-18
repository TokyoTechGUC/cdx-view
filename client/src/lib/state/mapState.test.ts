import { describe, it, expect, beforeEach } from 'vitest';
import { mapView, setOpacity } from './mapState.svelte';

describe('mapState', () => {
  beforeEach(() => {
    setOpacity(0.7);
  });

  describe('mapView.opacity', () => {
    it('defaults to 0.7', () => {
      expect(mapView.opacity).toBe(0.7);
    });
  });

  describe('setOpacity', () => {
    it('updates opacity to a valid value', () => {
      setOpacity(0.4);
      expect(mapView.opacity).toBe(0.4);
    });

    it('clamps to 0 when given a negative value', () => {
      setOpacity(-0.1);
      expect(mapView.opacity).toBe(0);
    });

    it('clamps to 1 when given a value above 1', () => {
      setOpacity(1.5);
      expect(mapView.opacity).toBe(1);
    });

    it('accepts 0 as a valid boundary value', () => {
      setOpacity(0);
      expect(mapView.opacity).toBe(0);
    });

    it('accepts 1 as a valid boundary value', () => {
      setOpacity(1);
      expect(mapView.opacity).toBe(1);
    });
  });
});
