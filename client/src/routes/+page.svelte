<script lang="ts">
  import { browser } from "$app/environment";
  import { goto } from "$app/navigation";
  import { base } from "$app/paths";
  import Map from "$lib/components/Map.svelte";
  import SidePanel from "$lib/components/SidePanel.svelte";
  import { datasetView } from "$lib/state/datasetState.svelte";
  import { backgroundView } from "$lib/state/backgroundLayerState.svelte";

  // Default closed on small screens so the map is visible first.
  const initialOpen = browser
    ? !window.matchMedia("(max-width: 767px)").matches
    : true;
  let panelOpen = $state(initialOpen);

  $effect(() => {
    if (!datasetView.dataset && backgroundView.layers.length === 0) {
      goto(`${base}/projects`);
    }
  });
</script>

{#if datasetView.dataset || backgroundView.layers.length > 0}
  <div class="layout">
    <SidePanel open={panelOpen} onClose={() => (panelOpen = false)} />
    <button
      class="open-panel"
      class:visible={!panelOpen}
      onclick={() => (panelOpen = true)}
      aria-label="Open panel"
      title="Open panel"
    >
      ≡
    </button>
    <div class="map-area">
      <Map {panelOpen} />
    </div>
  </div>
{/if}

<style>
  .layout {
    display: flex;
    width: 100%;
    height: 100dvh;
  }
  .map-area {
    flex: 1;
    min-width: 0;
    position: relative;
  }
  /* Open-panel button is mobile-only, shown when the panel is closed. */
  .open-panel {
    display: none;
    position: absolute;
    top: 12px;
    left: 12px;
    z-index: 5;
    width: 36px;
    height: 36px;
    align-items: center;
    justify-content: center;
    border: 1px solid #ccc;
    border-radius: 6px;
    background: #fff;
    font-size: 1.1rem;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  }
  .open-panel:hover {
    background: #f5f5f5;
  }
  @media (max-width: 767px) {
    .open-panel.visible {
      display: flex;
    }
  }
</style>
