<script lang="ts">
  import type { Competition, Tag, TagGroup, Mode, QueryState } from '$lib/types';
  import { emptyQuery } from '$lib/types';
  import { search } from '$lib/search';
  import FacetSection from '$lib/FacetSection.svelte';
  import ResultCard from '$lib/ResultCard.svelte';

  interface Data {
    competitions: Competition[];
    tags: Tag[];
    generatedAt: string;
  }
  let { data }: { data: Data } = $props();

  const tagsByGroup: Record<TagGroup, Tag[]> = $derived.by(() => {
    const out: Record<TagGroup, Tag[]> = { data: [], task: [], domain: [] };
    for (const t of data.tags) out[t.group].push(t);
    return out;
  });

  // Reverse lookup so result cards can render display names.
  const tagsBySlug: Map<string, Tag> = $derived(new Map(data.tags.map((t) => [t.slug, t])));

  // The whole query lives in one rune so updates are atomic.
  let query = $state<QueryState>(emptyQuery());

  // Run the search synchronously on every keystroke. ~1ms on 10k rows.
  const results: Competition[] = $derived(search(data.competitions, query));

  // Helpers that update one facet at a time without creating a new top-level
  // object on every keystroke.
  function updateFacet(group: TagGroup, next: { selected: string[]; mode: Mode }) {
    query[group] = next;
  }

  function clearAll() {
    query = emptyQuery();
  }

  // Whether any filter is active (controls "clear" button visibility).
  const hasActiveFilters = $derived(
    query.text !== '' ||
      query.data.selected.length > 0 ||
      query.task.selected.length > 0 ||
      query.domain.selected.length > 0 ||
      query.rewardType !== '' ||
      query.metricContains !== ''
  );

  // Pretty count for the header.
  const counts = $derived({
    total: data.competitions.length,
    showing: results.length
  });

  // ISO -> human-friendly "N days ago".
  function relativeAge(iso: string): string {
    const ms = Date.now() - new Date(iso).getTime();
    const days = Math.floor(ms / 86400000);
    if (days < 1) return 'today';
    if (days < 2) return 'yesterday';
    if (days < 30) return `${days} days ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`;
    const years = Math.floor(days / 365);
    return `${years} year${years === 1 ? '' : 's'} ago`;
  }
</script>

<div class="app">
  <header class="header">
    <span class="app-name">kaggle-finder</span>
    <span class="meta">
      {counts.total.toLocaleString()} competitions · updated {relativeAge(data.generatedAt)}
    </span>
  </header>

  <input
    class="search"
    type="text"
    placeholder="Search title, subtitle, or metric description…"
    bind:value={query.text}
  />

  <FacetSection
    label="Data type"
    tags={tagsByGroup.data}
    selected={query.data.selected}
    mode={query.data.mode}
    onChange={(next) => updateFacet('data', next)}
  />

  <FacetSection
    label="Task"
    tags={tagsByGroup.task}
    selected={query.task.selected}
    mode={query.task.mode}
    onChange={(next) => updateFacet('task', next)}
  />

  <FacetSection
    label="Domain"
    optional
    tags={tagsByGroup.domain}
    selected={query.domain.selected}
    mode={query.domain.mode}
    onChange={(next) => updateFacet('domain', next)}
  />

  <div class="misc">
    <div class="field">
      <span class="lbl">reward</span>
      <select bind:value={query.rewardType}>
        <option value="">any</option>
        <option value="USD">USD prize</option>
        <option value="Knowledge">knowledge</option>
        <option value="Jobs">jobs</option>
        <option value="Kudos">kudos</option>
        <option value="Swag">swag</option>
      </select>
    </div>
    <div class="field">
      <span class="lbl">metric</span>
      <input type="text" placeholder="any" bind:value={query.metricContains} />
    </div>
    <div class="field spacer">
      <span class="lbl">sort</span>
      <select bind:value={query.sort}>
        <option value="recent">most recent</option>
        <option value="oldest">oldest first</option>
      </select>
    </div>
  </div>

  <div class="results-head">
    <span class="meta">{counts.showing.toLocaleString()} results</span>
    {#if hasActiveFilters}
      <button class="clear" type="button" onclick={clearAll}>clear</button>
    {/if}
  </div>

  {#if results.length === 0}
    <p class="empty">No competitions match these filters.</p>
  {:else}
    {#each results.slice(0, 50) as c (c.id)}
      <ResultCard competition={c} tagsByslug={tagsBySlug} />
    {/each}
    {#if results.length > 50}
      <div class="more">
        <span class="meta">{(results.length - 50).toLocaleString()} more results</span>
      </div>
    {/if}
  {/if}
</div>

<style>
  .app {
    max-width: 760px;
    margin: 0 auto;
    padding: 2rem 1rem 4rem;
  }

  .header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 0.5px solid var(--border-tertiary);
    margin-bottom: 1.25rem;
  }
  .app-name {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 500;
  }

  .search {
    width: 100%;
    height: 40px;
    padding: 0 12px;
    font-size: 14px;
    border: 0.5px solid var(--border-tertiary);
    border-radius: var(--radius-md);
    background: var(--bg-surface);
    margin-bottom: 1.5rem;
    outline: none;
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  .search:focus {
    border-color: var(--border-secondary);
    box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.04);
  }

  .misc {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 12px 0;
    border-top: 0.5px solid var(--border-tertiary);
    border-bottom: 0.5px solid var(--border-tertiary);
    margin-bottom: 1.25rem;
    font-size: 13px;
    flex-wrap: wrap;
  }
  .field {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .spacer { margin-left: auto; }
  .lbl { color: var(--text-secondary); }

  .misc select,
  .misc input[type='text'] {
    font-size: 13px;
    padding: 4px 8px;
    background: var(--bg-surface);
    color: var(--text-primary);
    border: 0.5px solid var(--border-tertiary);
    border-radius: var(--radius-md);
    outline: none;
  }
  .misc input[type='text'] { width: 90px; }

  .meta {
    font-size: 11px;
    color: var(--text-tertiary);
    font-family: var(--font-mono);
  }

  .results-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }
  .clear {
    font-size: 11px;
    font-family: var(--font-mono);
    color: var(--text-tertiary);
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
  }
  .clear:hover {
    color: var(--text-primary);
    background: var(--bg-secondary);
  }

  .empty {
    padding: 2.5rem 0;
    text-align: center;
    color: var(--text-tertiary);
    font-size: 13px;
    border-top: 0.5px solid var(--border-tertiary);
  }
  .more {
    text-align: center;
    padding: 1.25rem 0 0.5rem;
  }
</style>
