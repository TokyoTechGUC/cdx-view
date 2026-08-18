<script lang="ts">
	import { onDestroy } from 'svelte';
	import { datasetView, setTimeIndex, stepTime } from '$lib/state/datasetState.svelte';
	import { formatTime } from '$lib/utils/formatTime';

	const PLAY_INTERVAL_MS = 800;

	let isPlaying = $state(false);
	let playTimer: ReturnType<typeof setInterval> | null = null;

	const times = $derived(datasetView.times);
	const total = $derived(times?.length ?? 0);
	// timeIndex is guaranteed non-null when `times && total > 0` (see template
	// guard below); the `?? 0` is a TypeScript-narrowing fallback only.
	const sliderIndex = $derived(datasetView.timeIndex ?? 0);
	const currentTime = $derived(times?.[sliderIndex] ?? '');
	const canPrev = $derived(sliderIndex > 0);
	const canNext = $derived(sliderIndex < total - 1);


	function stopTimer() {
		if (playTimer) {
			clearInterval(playTimer);
			playTimer = null;
		}
	}

	function play() {
		if (total === 0) return;
		if (sliderIndex >= total - 1) setTimeIndex(0);
		isPlaying = true;
		playTimer = setInterval(() => {
			if ((datasetView.timeIndex ?? 0) >= total - 1) {
				pause();
				return;
			}
			stepTime(1);
		}, PLAY_INTERVAL_MS);
	}

	function pause() {
		isPlaying = false;
		stopTimer();
	}

	function togglePlay() {
		if (isPlaying) pause();
		else play();
	}

	function onSliderInput(e: Event) {
		const value = parseInt((e.target as HTMLInputElement).value, 10);
		setTimeIndex(value);
	}

	function onSliderDown() {
		if (isPlaying) pause();
	}

	function stepPrev() {
		if (canPrev) stepTime(-1);
	}

	function stepNext() {
		if (canNext) stepTime(1);
	}

	onDestroy(pause);
</script>

{#if times && total > 0}
	<div class="time-slider">
		<button
			class="ctrl"
			onclick={stepPrev}
			disabled={!canPrev}
			aria-label="Previous time step"
			title="Previous"
		>
			⏮
		</button>
		<button
			class="ctrl play"
			onclick={togglePlay}
			aria-label={isPlaying ? 'Pause' : 'Play'}
			title={isPlaying ? 'Pause' : 'Play'}
		>
			{isPlaying ? '⏸' : '▶'}
		</button>
		<button
			class="ctrl"
			onclick={stepNext}
			disabled={!canNext}
			aria-label="Next time step"
			title="Next"
		>
			⏭
		</button>

		<input
			class="scrubber"
			type="range"
			min="0"
			max={total - 1}
			step="1"
			value={sliderIndex}
			oninput={onSliderInput}
			onpointerdown={onSliderDown}
			aria-label="Time scrubber"
		/>

		<div class="readout">
			<span class="time">{formatTime(currentTime)}</span>
			<span class="counter">{sliderIndex + 1} / {total}</span>
		</div>
	</div>
{/if}

<style>
	.time-slider {
		position: absolute;
		left: 50%;
		bottom: 24px;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		width: min(720px, calc(100% - 32px));
		box-sizing: border-box;
		background: rgba(20, 20, 20, 0.85);
		color: #fff;
		border-radius: 10px;
		box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
		font-family:
			system-ui,
			-apple-system,
			sans-serif;
		font-size: 0.9rem;
		z-index: 10;
		backdrop-filter: blur(6px);
	}

	.ctrl {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: none;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.12);
		color: #fff;
		font-size: 0.95rem;
		cursor: pointer;
		transition: background 0.15s ease;
	}

	.ctrl:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.22);
	}

	.ctrl:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.ctrl.play {
		width: 38px;
		height: 38px;
		font-size: 1.05rem;
		background: #2196f3;
	}

	.ctrl.play:hover {
		background: #1d8de2;
	}

	.scrubber {
		flex: 1;
		appearance: none;
		height: 4px;
		background: rgba(255, 255, 255, 0.25);
		border-radius: 2px;
		outline: none;
		cursor: pointer;
	}

	.scrubber::-webkit-slider-thumb {
		appearance: none;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: #2196f3;
		border: 2px solid #fff;
		cursor: pointer;
	}

	.scrubber::-moz-range-thumb {
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: #2196f3;
		border: 2px solid #fff;
		cursor: pointer;
	}

	.readout {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		line-height: 1.2;
		flex-shrink: 0;
	}

	.time {
		font-variant-numeric: tabular-nums;
		font-weight: 500;
		white-space: nowrap;
	}

	.counter {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.65);
		font-variant-numeric: tabular-nums;
	}

	@media (max-width: 767px) {
		.time-slider {
			flex-wrap: wrap;
			gap: 0.4rem;
			padding: 0.5rem 0.6rem;
			font-size: 0.8rem;
		}
		.ctrl {
			width: 28px;
			height: 28px;
			font-size: 0.85rem;
		}
		.ctrl.play {
			width: 32px;
			height: 32px;
			font-size: 0.95rem;
		}
		.scrubber {
			min-width: 80px;
		}
		.readout {
			flex-basis: 100%;
			flex-direction: row;
			align-items: center;
			justify-content: space-between;
			margin-top: 0.1rem;
			padding-top: 0.3rem;
			border-top: 1px solid rgba(255, 255, 255, 0.12);
		}
		.time {
			font-size: 0.75rem;
		}
		.counter {
			font-size: 0.7rem;
		}
	}
</style>
