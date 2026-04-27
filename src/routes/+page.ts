import type { PageLoad } from './$types';
import { loadBundle } from '$lib/data';

export const load: PageLoad = async ({ fetch }) => {
  const bundle = await loadBundle(fetch);
  return bundle;
};
