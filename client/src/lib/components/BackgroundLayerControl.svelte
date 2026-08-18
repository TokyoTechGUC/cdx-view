<script lang="ts">
  import type { BackgroundLayerEntry } from "$lib/state/backgroundLayerState.svelte";
  import {
    toggleBackgroundLayer,
    setBackgroundRescale,
    clearBackgroundRescale,
  } from "$lib/state/backgroundLayerState.svelte";
  import Colorbar from "./Colorbar.svelte";
  import ColorLegend from "./ColorLegend.svelte";
  import { isJsonColormap } from "$lib/colormapFormat";

  let { entry }: { entry: BackgroundLayerEntry } = $props();

  const defaultRescale = (): [number, number] =>
    entry.rescale ?? [entry.variable.vmin, entry.variable.vmax];

  let inputMin = $state(defaultRescale()[0].toFixed(2));
  let inputMax = $state(defaultRescale()[1].toFixed(2));
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  function onRescaleInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const min = parseFloat(inputMin);
      const max = parseFloat(inputMax);
      if (!isNaN(min) && !isNaN(max) && min < max) {
        setBackgroundRescale(entry.dataset.id, entry.variable.name, min, max);
      }
    }, 300);
  }

  function onReset() {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    clearBackgroundRescale(entry.dataset.id, entry.variable.name);
    inputMin = entry.variable.vmin.toFixed(2);
    inputMax = entry.variable.vmax.toFixed(2);
  }
</script>

<label class="bg-layer-option">
  <input
    type="checkbox"
    checked={entry.visible}
    onchange={() =>
      toggleBackgroundLayer(entry.dataset.id, entry.variable.name)}
  />
  <span class="bg-layer-label">{entry.variable.name}</span>
</label>
{#if entry.visible}
  <div class="bg-colorbar-slot">
    {#if isJsonColormap(entry.variable.colormap)}
      <ColorLegend
        colormap={entry.variable.colormap ?? ""}
        units={entry.variable.units}
      />
    {:else}
      <Colorbar
        name={entry.variable.colormap ?? "viridis"}
        units={entry.variable.units}
        bind:editMin={inputMin}
        bind:editMax={inputMax}
        onrescale={onRescaleInput}
        onreset={onReset}
      />
    {/if}
  </div>
{/if}

<style>
  .bg-layer-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
    cursor: pointer;
    font-size: 0.9rem;
  }
  .bg-layer-label {
    color: #444;
  }
  .bg-colorbar-slot {
    margin: 0.25rem 0 0.5rem 1.5rem;
  }
</style>
