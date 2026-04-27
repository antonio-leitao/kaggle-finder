<script lang="ts">
  import type { Mode, Tag } from '$lib/types';

  interface Props {
    label: string;
    optional?: boolean;
    tags: Tag[];
    selected: string[];
    mode: Mode;
    onChange: (next: { selected: string[]; mode: Mode }) => void;
  }

  let { label, optional = false, tags, selected, mode, onChange }: Props = $props();

  function toggle(slug: string) {
    const isOn = selected.includes(slug);
    const next = isOn ? selected.filter((s) => s !== slug) : [...selected, slug];
    onChange({ selected: next, mode });
  }

  function setMode(next: Mode) {
    if (next === mode) return;
    onChange({ selected, mode: next });
  }
</script>

<section class="facet">
  <div class="head">
    <div class="label">
      {label}{#if optional}<span class="opt">· optional</span>{/if}
    </div>
    <div class="mode" role="tablist" aria-label="{label} match mode">
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'any'}
        class:on={mode === 'any'}
        onclick={() => setMode('any')}
      >any</button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'all'}
        class:on={mode === 'all'}
        onclick={() => setMode('all')}
      >all</button>
    </div>
  </div>
  <div class="chips">
    {#each tags as t (t.slug)}
      <button
        type="button"
        class="chip"
        class:on={selected.includes(t.slug)}
        class:other={t.slug.endsWith('-other')}
        aria-pressed={selected.includes(t.slug)}
        onclick={() => toggle(t.slug)}
      >{t.name}{#if t.otherCount}<span class="count"> ·&nbsp;{t.otherCount}</span>{/if}</button>
    {/each}
  </div>
</section>

<style>
  .facet { margin-bottom: 1.25rem; }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .label {
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .opt {
    color: var(--text-tertiary);
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    margin-left: 4px;
  }

  .mode {
    display: inline-flex;
    align-items: center;
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-tertiary);
    gap: 2px;
    padding: 2px;
    background: var(--bg-secondary);
    border-radius: var(--radius-md);
  }
  .mode > button {
    padding: 3px 11px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: inherit;
    cursor: pointer;
    font: inherit;
  }
  .mode > button.on {
    background: var(--bg-surface);
    color: var(--text-primary);
    font-weight: 500;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 12px;
    line-height: 1;
    border: 0.5px solid var(--border-tertiary);
    color: var(--text-secondary);
    background: transparent;
    cursor: pointer;
    transition: all 120ms ease;
    font-family: inherit;
  }
  .chip:hover {
    border-color: var(--border-secondary);
    color: var(--text-primary);
  }
  .chip.on {
    background: var(--bg-info);
    color: var(--text-info);
    border-color: transparent;
    font-weight: 500;
  }
  .chip.other {
    font-style: italic;
  }
  .count {
    font-style: normal;
    font-family: var(--font-mono);
    font-size: 10px;
    opacity: 0.7;
  }
</style>
