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
}

export interface Tag {
  slug: string; // stable key — matches Competition.tagSlugs
  name: string; // display name
  group: TagGroup; // bucket the tag belongs to in our UI
}

// We surface three curated buckets plus a catch-all for everything else.
export type TagGroup = "data" | "task" | "domain" | "other";

export type Mode = "any" | "all";

export interface QueryState {
  text: string;
  data: { selected: string[]; mode: Mode };
  task: { selected: string[]; mode: Mode };
  domain: { selected: string[]; mode: Mode };
  other: { selected: string[]; mode: Mode };
  rewardType: "" | "USD" | "Knowledge" | "Kudos" | "Jobs" | "Swag";
  metricContains: string;
  sort: "recent" | "oldest";
}

export const emptyQuery = (): QueryState => ({
  text: "",
  data: { selected: [], mode: "all" },
  task: { selected: [], mode: "any" },
  domain: { selected: [], mode: "any" },
  other: { selected: [], mode: "any" },
  rewardType: "",
  metricContains: "",
  sort: "recent",
});
