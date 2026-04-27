<script lang="ts">
  import type { Competition, Tag } from '$lib/types';
  import { competitionUrl, formatMeta, thumbUrl } from '$lib/search';

  interface Props {
    competition: Competition;
    tagsByslug: Map<string, Tag>;
  }

  let { competition: c, tagsByslug }: Props = $props();

  // The Kaggle thumbnail bucket isn't 100% complete; if it 404s, fall back to a
  // colored monogram tile keyed off the slug.
  let imgFailed = $state(false);

  const monogram = $derived(c.title.replace(/[^A-Za-z]/g, '').slice(0, 2).toUpperCase() || '??');

  // Deterministic color from the slug so the same competition always gets the
  // same fallback color across renders.
  const palette = ['c-blue', 'c-teal', 'c-amber', 'c-coral', 'c-purple'];
  const colorClass = $derived(palette[hash(c.slug) % palette.length]);

  function hash(s: string): number {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    return Math.abs(h);
  }

  // Render up to 5 tags inline; rest collapse silently.
  const visibleTags = $derived(c.tagSlugs.slice(0, 5));
</script>

<a class="card" href={competitionUrl(c.slug)} target="_blank" rel="noopener noreferrer">
  {#if imgFailed}
    <div class="thumb {colorClass}" aria-hidden="true">{monogram}</div>
  {:else}
    <img
      class="thumb-img"
      src={thumbUrl(c.id)}
      alt=""
      loading="lazy"
      onerror={() => (imgFailed = true)}
    />
  {/if}

  <div class="content">
    <h3 class="title">{c.title}</h3>
    {#if c.subtitle}
      <p class="sub">{c.subtitle}</p>
    {/if}
    {#if visibleTags.length}
      <div class="tags">
        {#each visibleTags as slug (slug)}
          <span class="tag">{tagsByslug.get(slug)?.name ?? slug}</span>
        {/each}
      </div>
    {/if}
    <div class="meta">{formatMeta(c)}</div>
  </div>
</a>

<style>
  .card {
    display: flex;
    gap: 14px;
    padding: 16px 0;
    border-top: 0.5px solid var(--border-tertiary);
    color: inherit;
  }
  .card:hover .title { color: var(--text-info); }

  .thumb,
  .thumb-img {
    width: 76px;
    height: 76px;
    flex-shrink: 0;
    border-radius: var(--radius-md);
    background: var(--bg-secondary);
    object-fit: cover;
  }
  .thumb {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 500;
    font-family: var(--font-mono);
    letter-spacing: -0.02em;
  }
  .thumb.c-blue   { background: #e6f1fb; color: #0c447c; }
  .thumb.c-teal   { background: #e1f5ee; color: #085041; }
  .thumb.c-amber  { background: #faeeda; color: #633806; }
  .thumb.c-coral  { background: #faece7; color: #712b13; }
  .thumb.c-purple { background: #eeedfe; color: #3c3489; }

  .content { flex: 1; min-width: 0; }
  .title {
    font-size: 15px;
    font-weight: 500;
    margin: 0 0 4px;
    transition: color 120ms ease;
  }
  .sub {
    font-size: 13px;
    color: var(--text-secondary);
    margin: 0 0 10px;
    line-height: 1.55;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 8px;
  }
  .tag {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--bg-secondary);
    color: var(--text-secondary);
  }
  .meta {
    font-size: 11px;
    color: var(--text-tertiary);
    font-family: var(--font-mono);
  }
</style>
