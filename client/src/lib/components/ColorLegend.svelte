<script lang="ts">
  import { parseColormapSwatches } from "$lib/colormapFormat";

  interface Props {
    colormap: string;
    units: string | null;
  }
  let { colormap, units }: Props = $props();

  const swatches = $derived(parseColormapSwatches(colormap) ?? []);
</script>

<div class="color-legend">
  {#each swatches as swatch (swatch.label)}
    <div class="swatch">
      <span
        class="swatch-color"
        style="background: rgba({swatch.color[0]}, {swatch.color[1]}, {swatch
          .color[2]}, {(swatch.color[3] / 255).toFixed(2)})"
      ></span>
      <span class="swatch-label"
        >{swatch.label}{#if units}&nbsp;{units}{/if}</span
      >
    </div>
  {/each}
</div>

<style>
  .color-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 0.75rem;
    font-size: 0.75rem;
    color: #555;
  }
  .swatch {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }
  .swatch-color {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    flex-shrink: 0;
  }
  .swatch-label {
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
</style>
