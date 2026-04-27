import type { Competition, Tag } from './types';
import { base } from '$app/paths';

interface Bundle {
  competitions: Competition[];
  tags: Tag[];
  generatedAt: string;
}

let cache: Promise<Bundle> | null = null;

export function loadBundle(fetchFn: typeof fetch = fetch): Promise<Bundle> {
  if (cache) return cache;
  cache = (async () => {
    const res = await fetchFn(`${base}/data/competitions.json`);
    if (!res.ok) {
      throw new Error(`failed to load competitions.json: HTTP ${res.status}`);
    }
    const data = (await res.json()) as Bundle;
    return data;
  })();
  return cache;
}
