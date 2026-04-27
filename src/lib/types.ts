// Shape of one row in /data/competitions.json.
//
// `id` is the Kaggle CompetitionId.
export interface Competition {
  id: number;
  slug: string;
  title: string;
  subtitle: string | null;
  hostSegment: string | null; // Featured | Research | Playground | ...
  deadline: string | null; // ISO date
  metric: string | null; // Evaluation metric name
  metricDescription: string | null; // searchable, longer
  rewardType: string | null; // USD | Knowledge | Kudos | Jobs | Swag
  rewardQuantity: number | null; // present when rewardType === 'USD'
  tagSlugs: string[]; // refers to Tag.slug
  tagText: string; // joined display names of the comp's
  // raw tags, including long-tail tags
  // that the UI rolled up into "other".
  // Used for free-text tag search.
}

export interface Tag {
  slug: string; // stable key — matches Competition.tagSlugs
  name: string; // display name (may be "other" for the catch-all)
  group: TagGroup; // bucket the tag belongs to in our UI
  otherCount?: number; // present only on "*-other" chips: how many
  // long-tail tags are rolled up into this chip.
}

// Three curated facets, no separate "other" group anymore — instead each
// facet has an "other" chip as its last entry.
export type TagGroup = "data" | "task" | "domain";

export type Mode = "any" | "all";

export interface QueryState {
  text: string;
  data: { selected: string[]; mode: Mode };
  task: { selected: string[]; mode: Mode };
  domain: { selected: string[]; mode: Mode };
  rewardType: "" | "USD" | "Knowledge" | "Kudos" | "Jobs" | "Swag";
  metricContains: string;
  sort: "recent" | "oldest";
}

export const emptyQuery = (): QueryState => ({
  text: "",
  data: { selected: [], mode: "all" },
  task: { selected: [], mode: "any" },
  domain: { selected: [], mode: "any" },
  rewardType: "",
  metricContains: "",
  sort: "recent",
});
