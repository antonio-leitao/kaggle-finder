// Shape of one row in /data/competitions.json.
//
// `id` is the Kaggle CompetitionId; thumbnails are derived from it via
// https://storage.googleapis.com/kaggle-competitions/kaggle/{id}/logos/thumb76_76.png
export interface Competition {
  id: number;
  slug: string;
  title: string;
  subtitle: string | null;
  hostSegment: string | null;       // Featured | Research | Playground | ...
  deadline: string | null;          // ISO date
  metric: string | null;            // Evaluation metric name
  metricDescription: string | null; // searchable, longer
  rewardType: string | null;        // USD | Knowledge | Kudos | Jobs | Swag
  rewardQuantity: number | null;    // present when rewardType === 'USD'
  tagSlugs: string[];               // refers to Tag.slug
}

export interface Tag {
  slug: string;       // stable key — matches Competition.tagSlugs
  name: string;       // display name
  group: TagGroup;    // bucket the tag belongs to in our UI
}

// We only surface three buckets; everything else from Meta Kaggle is dropped
// at build time. Keeping the union narrow here lets the UI render statically.
export type TagGroup = 'data' | 'task' | 'domain';

// What gets persisted in the URL hash for shareable links.
export type Mode = 'any' | 'all';

export interface QueryState {
  text: string;
  data: { selected: string[]; mode: Mode };
  task: { selected: string[]; mode: Mode };
  domain: { selected: string[]; mode: Mode };
  rewardType: '' | 'USD' | 'Knowledge' | 'Kudos' | 'Jobs' | 'Swag';
  metricContains: string;
  sort: 'recent' | 'oldest';
}

export const emptyQuery = (): QueryState => ({
  text: '',
  data:   { selected: [], mode: 'all' },
  task:   { selected: [], mode: 'any' },
  domain: { selected: [], mode: 'any' },
  rewardType: '',
  metricContains: '',
  sort: 'recent'
});
