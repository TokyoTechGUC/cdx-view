<script lang="ts">
  import { untrack } from "svelte";
  import {
    datasetView,
    selectVariable,
    setVariableColormap,
    setVariableTimes,
    setVariableRescale,
    clearVariableRescale,
  } from "$lib/state/datasetState.svelte";
  import {
    projectView,
    setActiveDataset,
  } from "$lib/state/projectState.svelte";
  import { backgroundView } from "$lib/state/backgroundLayerState.svelte";
  import BackgroundLayerControl from "./BackgroundLayerControl.svelte";
  import { getDatasetInfo } from "$lib/api/tileServer";
  import { COLORMAPS } from "$lib/colormaps";
  import { isJsonColormap } from "$lib/colormapFormat";
  import Colorbar from "./Colorbar.svelte";
  import ColorLegend from "./ColorLegend.svelte";

  interface Props {
    open?: boolean;
    onClose?: () => void;
  }
  let { open = true, onClose }: Props = $props();

  let inputMin = $state("");
  let inputMax = $state("");
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  function fmtRescale(v: number): string {
    return v.toFixed(2);
  }

  // Sync inputs whenever the selected variable changes.
  // Read rescale untracked so typing doesn't trigger a re-sync loop.
  $effect(() => {
    const variable = datasetView.selectedVariable;
    if (!variable) {
      inputMin = "";
      inputMax = "";
      return;
    }
    const [min, max] = untrack(() => datasetView.selectedRescale) ?? [
      variable.vmin,
      variable.vmax,
    ];
    inputMin = fmtRescale(min);
    inputMax = fmtRescale(max);
  });

  function onRescaleInput() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const name = datasetView.selectedVariable?.name;
      if (!name) return;
      const min = parseFloat(inputMin);
      const max = parseFloat(inputMax);
      if (!isNaN(min) && !isNaN(max) && min < max) {
        setVariableRescale(name, min, max);
      }
    }, 300);
  }

  function onReset() {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    const variable = datasetView.selectedVariable;
    if (!variable) return;
    clearVariableRescale(variable.name);
    inputMin = fmtRescale(variable.vmin);
    inputMax = fmtRescale(variable.vmax);
  }

  async function onVariableChange(name: string) {
    selectVariable(name);
    const { dataset, selectedVariable: variable } = datasetView;
    if (
      variable &&
      dataset &&
      dataset.format !== "cog" &&
      variable.times === null
    ) {
      const info = await getDatasetInfo(dataset.id, name);
      if (info.times) setVariableTimes(name, info.times);
    }
  }

  async function onScenarioChange(e: Event) {
    const id = (e.target as HTMLSelectElement).value;
    setActiveDataset(id);
    const { dataset, selectedVariable: variable } = datasetView;
    if (
      variable &&
      dataset &&
      dataset.format !== "cog" &&
      variable.times === null
    ) {
      const info = await getDatasetInfo(dataset.id, variable.name);
      if (info.times) setVariableTimes(variable.name, info.times);
    }
  }

  // Colormap picker is disabled for now — see the commented-out <select>
  // below for why. Kept here so it's a quick uncomment to bring back.
  // function onColormapChange(e: Event) {
  //   const target = e.target as HTMLSelectElement;
  //   const variable = datasetView.selectedVariable;
  //   if (variable) setVariableColormap(variable.name, target.value);
  // }
</script>

<aside class="side-panel" class:open>
  <header class="header">
    <h2>{projectView.project?.title ?? datasetView.dataset?.name ?? ""}</h2>
    {#if onClose}
      <button
        class="close"
        onclick={onClose}
        aria-label="Close panel"
        title="Close">×</button
      >
    {/if}
  </header>

  <!-- {#if projectView.project?.description}
    <p class="description">{projectView.project.description}</p>
  {/if} -->

  {#if projectView.datasets.length > 1}
    <section class="section">
      <h3>Scenario</h3>
      <select
        class="scenario-select"
        value={projectView.activeDatasetId}
        onchange={onScenarioChange}
      >
        {#each projectView.datasets as dataset}
          <option value={dataset.id}>{dataset.name}</option>
        {/each}
      </select>
    </section>
  {/if}

  {#if datasetView.dataset}
    <p class="scenario-name">{datasetView.dataset.name}</p>
    {#if datasetView.dataset.description}
      <p class="scenario-desc">{datasetView.dataset.description}</p>
    {/if}
  {/if}

  {#if datasetView.dataset}
    <section class="section">
      <h3>Variable</h3>
      <div class="variables">
        {#each datasetView.dataset.variables as variable (variable.name)}
          <label class="variable-option">
            <input
              type="radio"
              name="variable"
              value={variable.name}
              checked={datasetView.selectedVariable?.name === variable.name}
              onchange={() => onVariableChange(variable.name)}
            />
            <span class="variable-name">{variable.name}</span>
            {#if variable.long_name}
              <span class="variable-long-name">{variable.long_name}</span>
            {/if}
            {#if variable.units}
              <span class="variable-units">{variable.units}</span>
            {/if}
          </label>
        {/each}
      </div>
    </section>
  {/if}

  {#if datasetView.selectedVariable}
    <section class="section">
      <h3>Colormap</h3>
      <!--
        Colormap picker is disabled: choosing a "correct" colormap requires
        domain knowledge most users don't have, and the dataset's registered
        default is usually the right choice. Left commented out rather than
        removed since we may want to bring this back.
        <select
          class="colormap-select"
          value={datasetView.selectedColormap}
          onchange={onColormapChange}
        >
          {#each COLORMAPS as cm}
            <option value={cm}>{cm}</option>
          {/each}
        </select>
      -->
      <div class="colorbar-slot">
        {#if isJsonColormap(datasetView.selectedColormap)}
          <ColorLegend
            colormap={datasetView.selectedColormap}
            units={datasetView.selectedVariable.units}
          />
        {:else}
          <Colorbar
            name={datasetView.selectedColormap}
            units={datasetView.selectedVariable.units}
            bind:editMin={inputMin}
            bind:editMax={inputMax}
            onrescale={onRescaleInput}
            onreset={onReset}
          />
        {/if}
      </div>
    </section>
  {/if}
  {#if backgroundView.layers.length > 0}
    <section class="section">
      <h3>Background Layers</h3>
      <div class="bg-layers">
        {#each backgroundView.layers as entry (entry.dataset.id + "/" + entry.variable.name)}
          <BackgroundLayerControl {entry} />
        {/each}
      </div>
    </section>
  {/if}
</aside>

<style>
  .side-panel {
    background: #ffffff;
    border-right: 1px solid #e0e0e0;
    width: 320px;
    height: 100dvh;
    overflow-y: auto;
    padding: 1rem 1.25rem;
    box-sizing: border-box;
    font-family:
      system-ui,
      -apple-system,
      sans-serif;
    color: #222;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .header h2 {
    margin: 0;
    font-size: 1.05rem;
    line-height: 1.3;
    word-break: break-word;
  }
  .close {
    /* Desktop: panel can't be closed — hide the × button. */
    display: none;
    border: none;
    background: transparent;
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
    color: #666;
    padding: 0 0.25rem;
  }
  .close:hover {
    color: #222;
  }
  .description {
    margin: 0.5rem 0 1rem;
    font-size: 0.85rem;
    color: #666;
    line-height: 1.4;
  }
  .section {
    margin-top: 1rem;
  }
  .section h3 {
    margin: 0 0 0.5rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
  }
  .variables {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .variable-option {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.25rem 0;
    cursor: pointer;
    font-size: 0.9rem;
  }
  .variable-name {
    font-family: monospace;
    color: #2196f3;
  }
  .variable-long-name {
    color: #666;
    font-size: 0.8rem;
  }
  .variable-units {
    color: #888;
    font-size: 0.8rem;
  }
  .scenario-select {
    width: 100%;
    padding: 0.4rem 0.5rem;
    font-size: 0.9rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: #fff;
    cursor: pointer;
  }
  /* Paired with the commented-out colormap <select> above.
  .colormap-select {
    width: 100%;
    padding: 0.4rem 0.5rem;
    font-size: 0.9rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: #fff;
    cursor: pointer;
  }
  */
  .scenario-name {
    margin: 0.5rem 0 0;
    font-size: 0.9rem;
    font-weight: 500;
    color: #222;
  }
  .scenario-desc {
    margin: 0.2rem 0 0;
    font-size: 0.8rem;
    color: #666;
    line-height: 1.4;
  }
  .colorbar-slot {
    margin-top: 0.5rem;
  }
  .bg-layers {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  @media (max-width: 767px) {
    .side-panel {
      position: absolute;
      top: 0;
      left: 0;
      z-index: 10;
      max-width: 100vw;
      box-shadow: 4px 0 12px rgba(0, 0, 0, 0.15);
      transform: translateX(-100%);
      transition: transform 0.2s ease;
    }
    .side-panel.open {
      transform: translateX(0);
    }
    .close {
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
</style>
