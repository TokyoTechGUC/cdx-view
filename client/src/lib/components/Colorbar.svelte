<script lang="ts">
  import { fetchColormap, type ColormapLUT } from '$lib/api/colormaps';

  interface Props {
    name: string;
    units: string | null;
    editMin: string;
    editMax: string;
    onrescale: () => void;
    onreset: () => void;
  }
  let { name, units, editMin = $bindable(), editMax = $bindable(), onrescale, onreset }: Props = $props();

  let lut: ColormapLUT | null = $state(null);

  $effect(() => {
    const currentName = name;
    fetchColormap(currentName)
      .then((l) => {
        // Guard against race: ignore if user has switched colormap since.
        if (currentName === name) lut = l;
      })
      .catch(() => {
        // Same race guard — don't clear the LUT for whatever's now selected.
        if (currentName === name) lut = null;
      });
  });

  const gradient = $derived(
    lut ? lutToGradient(lut) : 'linear-gradient(to right, #ddd, #ddd)',
  );

  function lutToGradient(table: ColormapLUT): string {
    const stops = table
      .map((rgba, i) => {
        const pct = (i / (table.length - 1)) * 100;
        return `rgba(${rgba[0]}, ${rgba[1]}, ${rgba[2]}, ${(rgba[3] / 255).toFixed(2)}) ${pct.toFixed(2)}%`;
      })
      .join(', ');
    return `linear-gradient(to right, ${stops})`;
  }


</script>

<div class="colorbar">
  <div class="bar" style="background: {gradient}"></div>
  <div class="labels">
    <input class="label-input" type="text" inputmode="decimal" bind:value={editMin} oninput={onrescale} />
    {#if units}<span class="units">{units}</span>{/if}
    <input class="label-input label-input--right" type="text" inputmode="decimal" bind:value={editMax} oninput={onrescale} />
    <button class="reset-btn" onclick={onreset} title="Reset to defaults">↺</button>
  </div>
</div>

<style>
  .colorbar {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .bar {
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(0, 0, 0, 0.1);
  }
  .labels {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    color: #555;
    font-variant-numeric: tabular-nums;
  }
  .units {
    color: #888;
    font-style: italic;
  }
  .label-input {
    width: 8ch;
    border: none;
    border-bottom: 1px solid #ccc;
    background: transparent;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
    color: #555;
    padding: 0;
    text-align: left;
  }
  .label-input--right {
    text-align: right;
  }
  .label-input:focus {
    outline: none;
    border-bottom-color: #2196f3;
  }
  .reset-btn {
    border: none;
    background: transparent;
    color: #bbb;
    cursor: pointer;
    font-size: 0.9rem;
    padding: 0;
    line-height: 1;
    flex-shrink: 0;
  }
  .reset-btn:hover {
    color: #555;
  }
</style>
