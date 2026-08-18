<script lang="ts">
	import { onMount, onDestroy, untrack } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import { datasetView } from '$lib/state/datasetState.svelte';
	import { mapView } from '$lib/state/mapState.svelte';
	import { tileJsonUrl, backgroundTileJsonUrl, getPointValue } from '$lib/api/tileServer';
	import { backgroundView } from '$lib/state/backgroundLayerState.svelte';
	import TimeSlider from './TimeSlider.svelte';
	import OpacityControl from './OpacityControl.svelte';

	interface Props {
		panelOpen?: boolean;
	}
	let { panelOpen = true }: Props = $props();

	function getCurrentTileJsonUrl(): string | null {
		const variable = datasetView.selectedVariable;
		const rescale = datasetView.selectedRescale;
		if (!datasetView.dataset || !variable || !rescale) return null;
		return tileJsonUrl(
			datasetView.dataset,
			variable,
			datasetView.timeIndex,
			datasetView.selectedColormap,
			rescale,
		);
	}

	let mapContainer: HTMLDivElement;
	let map: maplibregl.Map;
	let mapLoaded = $state(false);
	let lastZoomedDatasetId: string | null = null;

	function resetView() {
		const src = map.getSource('climate-tiles') as maplibregl.RasterTileSource | undefined;
		if (src?.bounds) {
			map.fitBounds(src.bounds, { padding: 40 });
		} else {
			map.flyTo({ center: [0, 0], zoom: 2 });
		}
	}

	let hoverValue = $state<number | null>(null);
	let hoverUnits = $state<string | null>(null);
	let hoverX = $state(0);
	let hoverY = $state(0);
	onMount(() => {
		map = new maplibregl.Map({
			container: mapContainer,
			style: {
				version: 8,
				sources: {
					'osm-tiles': {
						type: 'raster',
						tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
						tileSize: 256,
						attribution: '© OpenStreetMap contributors'
					}
				},
				layers: [
					{
						id: 'osm-tiles',
						type: 'raster',
						source: 'osm-tiles',
						minzoom: 0,
						maxzoom: 19
					}
				]
			},
			center: [0, 0],
			zoom: 2
		});

		map.on('load', () => {
			mapLoaded = true;
		});

		let hoverTimer: ReturnType<typeof setTimeout> | null = null;
		let hoverAbort: AbortController | null = null;

		function cancelHover() {
			if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
			if (hoverAbort) { hoverAbort.abort(); hoverAbort = null; }
		}

		map.on('mousemove', (e) => {
			hoverX = e.point.x;
			hoverY = e.point.y;
			cancelHover();
			hoverValue = null;

			const dataset = datasetView.dataset;
			const variable = datasetView.selectedVariable;
			if (!dataset || !variable) return;

			const bounds = (map.getSource('climate-tiles') as maplibregl.RasterTileSource | undefined)?.bounds;
			if (bounds) {
				const { lng, lat } = e.lngLat;
				const [west, south, east, north] = bounds;
				if (lng < west || lng > east || lat < south || lat > north) return;
			}

			const bidx = (datasetView.timeIndex ?? 0) + 1;
			hoverTimer = setTimeout(async () => {
				hoverAbort = new AbortController();
				try {
					hoverValue = await getPointValue(
						e.lngLat.lng, e.lngLat.lat,
						dataset, variable.name, bidx,
						hoverAbort.signal,
					);
					hoverUnits = variable.units;
				} catch {
					// aborted or network error — leave overlay hidden
				}
			}, 1000);
		});

		map.on('mouseout', () => {
			cancelHover();
			hoverValue = null;
		});
	});

	$effect(() => {
		if (!mapLoaded || !map) return;
		const url = getCurrentTileJsonUrl();
		if (map.getLayer('climate-tiles')) map.removeLayer('climate-tiles');
		if (map.getSource('climate-tiles')) map.removeSource('climate-tiles');
		if (!url) return;
		map.addSource('climate-tiles', {
			type: 'raster',
			url,
			tileSize: 256
		});
		map.addLayer({
			id: 'climate-tiles',
			type: 'raster',
			source: 'climate-tiles',
			minzoom: 0,
			maxzoom: 19,
			paint: {
				'raster-opacity': untrack(() => mapView.opacity)
			}
		});

		const currentDatasetId = datasetView.dataset?.id ?? null;
		if (!currentDatasetId || currentDatasetId === lastZoomedDatasetId) return;
		lastZoomedDatasetId = currentDatasetId;

		const onSourceData = (e: { sourceId: string; isSourceLoaded: boolean }) => {
			if (e.sourceId !== 'climate-tiles' || !e.isSourceLoaded) return;
			map.off('sourcedata', onSourceData);
			const src = map.getSource('climate-tiles') as maplibregl.RasterTileSource | undefined;
			if (src?.bounds) map.fitBounds(src.bounds, { padding: 40 });
		};
		map.on('sourcedata', onSourceData);
		return () => map.off('sourcedata', onSourceData);
	});

	$effect(() => {
		const opacity = mapView.opacity;
		if (mapLoaded && map.getLayer('climate-tiles')) {
			map.setPaintProperty('climate-tiles', 'raster-opacity', opacity);
		}
	});

	$effect(() => {
		if (!mapLoaded || !map) return;
		const visibleLayers = backgroundView.visibleLayers;
		const addedIds: string[] = [];

		for (const entry of visibleLayers) {
			const id = `bg-${entry.dataset.id}-${entry.variable.name}`;
			const url = backgroundTileJsonUrl(entry.dataset, entry.variable, entry.rescale ?? undefined);
			if (!map.getSource(id)) {
				map.addSource(id, { type: 'raster', url, tileSize: 256 });
			}
			if (!map.getLayer(id)) {
				map.addLayer(
					{ id, type: 'raster', source: id, paint: { 'raster-opacity': 0.8 } },
					map.getLayer('climate-tiles') ? 'climate-tiles' : undefined,
				);
			}
			addedIds.push(id);
		}

		return () => {
			for (const id of addedIds) {
				if (map.getLayer(id)) map.removeLayer(id);
				if (map.getSource(id)) map.removeSource(id);
			}
		};
	});

	onDestroy(() => {
		if (map) {
			map.remove();
		}
	});
</script>

<div class="map-wrapper">
	<div bind:this={mapContainer} class="map-container"></div>
	<TimeSlider />
	<OpacityControl {panelOpen} />
	<button class="reset-view" class:panel-open={panelOpen} onclick={resetView} aria-label="Reset view">&#8635; Reset View</button>
	{#if hoverValue !== null}
		<div class="hover-overlay" style="left: {hoverX}px; top: {hoverY}px;">
			{hoverValue.toFixed(2)}{hoverUnits ? ` ${hoverUnits}` : ''}
		</div>
	{/if}
</div>

<style>
	.map-wrapper {
		position: relative;
		width: 100%;
		height: 100%;
	}
	.map-container {
		width: 100%;
		height: 100%;
	}

	.reset-view {
		position: absolute;
		top: 12px;
		left: 12px;
		z-index: 10;
		padding: 0.5rem 0.75rem;
		background: rgba(20, 20, 20, 0.85);
		color: #fff;
		border: none;
		border-radius: 10px;
		box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
		font-family: system-ui, -apple-system, sans-serif;
		font-size: 0.85rem;
		backdrop-filter: blur(6px);
		cursor: pointer;
	}

	.reset-view:hover {
		background: rgba(40, 40, 40, 0.92);
	}

	@media (max-width: 767px) {
		.reset-view {
			top: 56px;
		}
		.reset-view.panel-open {
			display: none;
		}
	}

	.hover-overlay {
		position: absolute;
		transform: translate(12px, -100%);
		pointer-events: none;
		z-index: 10;
		padding: 0.35rem 0.6rem;
		background: rgba(20, 20, 20, 0.85);
		color: #fff;
		border-radius: 6px;
		font-family: system-ui, -apple-system, sans-serif;
		font-size: 0.8rem;
		font-variant-numeric: tabular-nums;
		backdrop-filter: blur(6px);
		white-space: nowrap;
	}
</style>
