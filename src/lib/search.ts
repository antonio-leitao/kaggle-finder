import type { Competition, QueryState } from './types';

// Match a tag-set against a competition given the chosen mode.
function matchTags(have: Set<string>, want: string[], mode: 'any' | 'all'): boolean {
  if (want.length === 0) return true;
  if (mode === 'all') {
    for (const w of want) if (!have.has(w)) return false;
    return true;
  }
  // any
  for (const w of want) if (have.has(w)) return true;
  return false;
}

function textMatch(c: Competition, needle: string): boolean {
  const n = needle.trim().toLowerCase();
  if (!n) return true;
  const hay = (
    (c.title ?? '') + ' ' +
    (c.subtitle ?? '') + ' ' +
    (c.metricDescription ?? '')
  ).toLowerCase();
  return hay.includes(n);
}

export function search(corpus: Competition[], q: QueryState): Competition[] {
  const filtered = corpus.filter((c) => {
    const tags = new Set(c.tagSlugs);
    if (!matchTags(tags, q.data.selected,   q.data.mode))   return false;
    if (!matchTags(tags, q.task.selected,   q.task.mode))   return false;
    if (!matchTags(tags, q.domain.selected, q.domain.mode)) return false;

    if (q.rewardType && c.rewardType !== q.rewardType) return false;

    if (q.metricContains.trim()) {
      const needle = q.metricContains.trim().toLowerCase();
      const m = (c.metric ?? '').toLowerCase();
      if (!m.includes(needle)) return false;
    }

    if (!textMatch(c, q.text)) return false;

    return true;
  });

  // Sort. Nulls always go last regardless of direction.
  filtered.sort((a, b) => {
    const ad = a.deadline ?? '';
    const bd = b.deadline ?? '';
    if (!ad && !bd) return 0;
    if (!ad) return 1;
    if (!bd) return -1;
    return q.sort === 'recent' ? bd.localeCompare(ad) : ad.localeCompare(bd);
  });

  return filtered;
}

// Stable Kaggle thumbnail URL. Falls back to a transparent pixel handled in CSS.
export function thumbUrl(id: number): string {
  return `https://storage.googleapis.com/kaggle-competitions/kaggle/${id}/logos/thumb76_76.png`;
}

export function competitionUrl(slug: string): string {
  return `https://www.kaggle.com/competitions/${slug}`;
}

// Format the meta line under each result.
export function formatMeta(c: Competition): string {
  const parts: string[] = [];
  if (c.hostSegment) parts.push(c.hostSegment);
  if (c.rewardType === 'USD' && c.rewardQuantity) {
    parts.push(`$${c.rewardQuantity.toLocaleString('en-US', { maximumFractionDigits: 0 })}`);
  } else if (c.rewardType) {
    parts.push(c.rewardType.toLowerCase());
  }
  if (c.metric) parts.push(c.metric);
  if (c.deadline) parts.push(c.deadline.slice(0, 4));
  return parts.join(' · ');
}
