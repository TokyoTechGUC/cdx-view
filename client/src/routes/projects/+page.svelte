<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { listProjects, getProject, getDatasetInfo } from '$lib/api/tileServer';
  import type { ProjectSummary } from '$lib/types';
  import { setProject } from '$lib/state/projectState.svelte';
  import { datasetView, setVariableTimes } from '$lib/state/datasetState.svelte';

  let projects: ProjectSummary[] = $state([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      projects = await listProjects();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Unknown error';
    } finally {
      loading = false;
    }
  });

  async function onSelectProject(summary: ProjectSummary) {
    const project = await getProject(summary.id);
    setProject(project);
    const { dataset, selectedVariable: selected } = datasetView;
    if (selected && dataset && dataset.format !== 'cog' && selected.times === null) {
      const info = await getDatasetInfo(dataset.id, selected.name);
      if (info.times) setVariableTimes(selected.name, info.times);
    }
    goto(`${base}/`);
  }
</script>

<div class="container">
  <h1>Select a Project</h1>

  {#if loading}
    <div class="status">Loading projects...</div>
  {:else if error}
    <div class="status error">Error: {error}</div>
  {:else if projects.length === 0}
    <div class="status">No projects available</div>
  {:else}
    <div class="grid">
      {#each projects as project}
        <button class="card" onclick={() => onSelectProject(project)}>
          <h2>{project.title}</h2>
          {#if project.description}
            <p class="description">{project.description}</p>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }

  h1 {
    font-size: 2rem;
    margin-bottom: 2rem;
    color: #333;
  }

  .status {
    text-align: center;
    padding: 2rem;
    font-size: 1.1rem;
  }

  .status.error {
    color: #d32f2f;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
  }

  .card:hover {
    border-color: #2196f3;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .card h2 {
    margin: 0 0 0.5rem 0;
    font-size: 1.3rem;
    color: #2196f3;
  }

  .description {
    margin: 0.5rem 0 0 0;
    font-size: 0.85rem;
    color: #999;
    line-height: 1.4;
  }
</style>
