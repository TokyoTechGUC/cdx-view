<script lang="ts">
  import { datasetView } from '$lib/state/datasetState.svelte';
  import { mapView, setOpacity } from '$lib/state/mapState.svelte';

  interface Props {
    panelOpen?: boolean;
  }
  let { panelOpen = true }: Props = $props();

  function onInput(e: Event) {
    setOpacity(parseFloat((e.target as HTMLInputElement).value));
  }
</script>

{#if datasetView.dataset}
  <div class="opacity-control" class:panel-open={panelOpen}>
    <span class="label">Opacity</span>
    <input
      class="slider"
      type="range"
      min="0"
      max="1"
      step="0.05"
      value={mapView.opacity}
      oninput={onInput}
      aria-label="Tile opacity"
    />
    <span class="value">{mapView.opacity.toFixed(2)}</span>
  </div>
{/if}

<style>
  .opacity-control {
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 0.75rem;
    background: rgba(20, 20, 20, 0.85);
    color: #fff;
    border-radius: 10px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
    font-family: system-ui, -apple-system, sans-serif;
    font-size: 0.85rem;
    backdrop-filter: blur(6px);
  }

  .label {
    flex-shrink: 0;
    color: rgba(255, 255, 255, 0.75);
  }

  .slider {
    width: 90px;
    appearance: none;
    height: 4px;
    background: rgba(255, 255, 255, 0.25);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .slider::-webkit-slider-thumb {
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #2196f3;
    border: 2px solid #fff;
    cursor: pointer;
  }

  .slider::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #2196f3;
    border: 2px solid #fff;
    cursor: pointer;
  }

  .value {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    flex-shrink: 0;
    min-width: 2.5ch;
    text-align: right;
  }

  @media (max-width: 767px) {
    .opacity-control.panel-open {
      display: none;
    }
  }
</style>
