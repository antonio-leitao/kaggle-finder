# kaggle-finder

A static, single-page search over finalized Kaggle competitions, filtered by
data type, task, and domain. Backed by Meta Kaggle (refreshed weekly), runs
entirely in the browser.

## Local dev

```sh
npm install
npm run dev
```

The app loads `/data/competitions.json`. A 20-row sample is committed under
`static/data/competitions.json` so the UI works out of the box.

## Build & deploy

```sh
npm run build      # outputs static site to ./build
npm run preview    # serve ./build locally
```

GitHub Actions deploys `main` to GitHub Pages automatically. To use a project
URL like `https://you.github.io/kaggle-finder`, add a repo variable
`BASE_PATH=/kaggle-finder` (Settings → Secrets and variables → Actions →
Variables). For a root user/org page, leave it unset.

## Data refresh

`scripts/build.py` reads three Meta Kaggle CSVs and produces the JSON the app
consumes. Run it manually:

```sh
mkdir -p meta-kaggle
for f in Tags.csv Competitions.csv CompetitionTags.csv; do
  kaggle datasets download kaggle/meta-kaggle -f "$f" -p meta-kaggle --unzip
done
python scripts/build.py --csv-dir meta-kaggle --out static/data/competitions.json
rm -rf meta-kaggle
```

Or wait for the weekly cron in `.github/workflows/refresh.yml`. It needs two
repo secrets: `KAGGLE_USERNAME` and `KAGGLE_KEY`
([create an API token](https://www.kaggle.com/settings/account)).

## What's in the JSON

```ts
{
  generatedAt: string,                 // ISO timestamp
  tags: { slug, name, group: 'data' | 'task' | 'domain' }[],
  competitions: {
    id, slug, title, subtitle,
    hostSegment, deadline, metric, metricDescription,
    rewardType, rewardQuantity,
    tagSlugs: string[]                  // refers to tags[].slug
  }[]
}
```

The taxonomy is fixed in `scripts/build.py`. Only competitions that have at
least one taxonomy tag are included. Adding a tag means editing both
`TAXONOMY` in `build.py` and rebuilding.

## Adapting the LLM contract

The `QueryState` type in `src/lib/types.ts` is the same shape an LLM step
should emit. To wire a "describe your problem" textbox that drives the same
search, parse natural language to `QueryState` server-side or in another
build step, then drop the result into the same `search()` function used by
the UI.

## Architecture

```
static/data/competitions.json    — single source of truth, ~6 MB at full size
src/lib/types.ts                 — shared types, including QueryState
src/lib/search.ts                — pure filter+sort, runs on every keystroke
src/lib/data.ts                  — fetch and cache the JSON
src/routes/+page.svelte          — the UI
scripts/build.py                 — Meta Kaggle CSVs → competitions.json
```

No backend, no DB, no wasm. Search runs in 1–2 ms on 10k rows because the
corpus is small enough to live in memory.
