#!/usr/bin/env python3
"""Build static/data/competitions.json from a Meta Kaggle dump.

Reads three CSVs from --csv-dir and projects fields the UI needs.

Tag routing:
- Each Kaggle tag has a FullPath (e.g. "subject > biology", "data type > image").
  We map the top-level FullPath segment to one of our three facets:
    data type             -> data
    task                  -> task
    technique             -> task     (mostly task-shaped: "time series",
                                       "computer vision", "recommender systems")
    subject               -> domain
    geography and places  -> domain
    language              -> domain
- Tags under audience / packages / architecture / analysis are dropped — they
  describe who or how, not what the problem is.
- Within each facet, the most-frequent tags become chips. Anything below the
  threshold collapses into a single "{facet}-other" tag the UI shows as a
  single chip per facet, but the chip's slug-set covers the whole long tail.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Tags below this competition count get collapsed into the per-facet "other"
# chip. From the data this gives ~6 data, ~7 task, ~25 domain chips.
OTHER_THRESHOLD = 5

# How a tag's top-level FullPath segment routes to one of our facets.
# Anything not in this map is dropped entirely.
PATH_TO_FACET: dict[str, str] = {
    "data type": "data",
    "task": "task",
    "technique": "task",
    "analysis": "task",
    "subject": "domain",
    "geography and places": "domain",
    "language": "domain",
}

# Per-tag overrides: some tags Meta Kaggle put in one bucket but actually
# belong elsewhere (or shouldn't be surfaced) for our purposes.
SLUG_OVERRIDES: dict[str, str] = {
    # technique tags that aren't really tasks
    "deep-learning": "DROP",
    "transfer-learning": "DROP",
    "neural-networks": "DROP",
    "ensembling": "DROP",
    "model-comparison": "DROP",
    "transformer": "DROP",
    "graph-neural-network": "DROP",
    # analysis tags that are noise, not task descriptors
    "data-cleaning": "DROP",
    "survey-analysis": "DROP",
    "statistical-analysis": "DROP",
    "exploratory-data-analysis": "DROP",
    "data-visualization": "DROP",
    # data-type-ish things
    "graph-data": "data",
    "multimodal-data": "data",
}

# Tag display-name overrides (slug -> nicer display name).
NAME_OVERRIDES: dict[str, str] = {
    "tabular-data": "tabular",
    "image-data": "image",
    "text-data": "text",
    "audio-data": "audio",
    "video-data": "video",
    "graph-data": "graph",
    "multimodal-data": "multimodal",
    "image-processing": "computer vision",
    "time-series-analysis": "time series",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_int(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def parse_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_iso_date(v: str | None) -> str | None:
    if not v:
        return None
    return v.split(" ", 1)[0].strip() or None


def is_truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"true", "1", "yes"}


def route(slug: str, fullpath: str) -> str | None:
    """Return one of {'data','task','domain'} or None if the tag is dropped."""
    if slug in SLUG_OVERRIDES:
        v = SLUG_OVERRIDES[slug]
        return None if v == "DROP" else v
    if not fullpath:
        return None
    top = fullpath.split(">", 1)[0].strip().lower()
    return PATH_TO_FACET.get(top)


def display_name(slug: str, raw_name: str) -> str:
    if slug in NAME_OVERRIDES:
        return NAME_OVERRIDES[slug]
    return (raw_name or slug.replace("-", " ")).strip().lower()


def build(csv_dir: Path, out: Path) -> None:
    tags_path = csv_dir / "Tags.csv"
    comp_path = csv_dir / "Competitions.csv"
    ct_path = csv_dir / "CompetitionTags.csv"
    for p in (tags_path, comp_path, ct_path):
        if not p.exists():
            sys.exit(f"missing {p}")

    # 1. Tags table -> TagId -> (slug, display_name, facet | None).
    tag_meta: dict[int, tuple[str, str, str | None]] = {}
    for row in read_csv(tags_path):
        tid = parse_int(row.get("Id"))
        slug = (row.get("Slug") or "").strip().lower()
        if tid is None or not slug:
            continue
        name = display_name(slug, (row.get("Name") or "").strip())
        facet = route(slug, (row.get("FullPath") or "").strip())
        tag_meta[tid] = (slug, name, facet)

    # 2. Competition -> set of (slug, facet) for tags that survived routing.
    comp_tags: dict[int, set[str]] = {}
    for row in read_csv(ct_path):
        cid = parse_int(row.get("CompetitionId"))
        tid = parse_int(row.get("TagId"))
        if cid is None or tid is None:
            continue
        meta = tag_meta.get(tid)
        if meta is None:
            continue
        slug, _, facet = meta
        if facet is None:
            continue
        comp_tags.setdefault(cid, set()).add(slug)

    # 3. Tag frequencies on finalized competitions.
    finalized_ids: set[int] = set()
    comp_rows: list[dict] = []
    for row in read_csv(comp_path):
        if not is_truthy(row.get("FinalLeaderboardHasBeenVerified")):
            continue
        cid = parse_int(row.get("Id"))
        if cid is None:
            continue
        finalized_ids.add(cid)
        comp_rows.append(row)

    freq: Counter[str] = Counter()
    for cid in finalized_ids:
        for slug in comp_tags.get(cid, ()):
            freq[slug] += 1

    # 4. Decide per-tag whether it's a chip or part of the facet's "other"
    # bucket. Build slug -> {chip_slug, facet, name}, where chip_slug is either
    # the original slug (popular tag) or "{facet}-other".
    OTHER_SLUGS = {"data": "data-other", "task": "task-other", "domain": "domain-other"}

    slug_to_chip: dict[str, str] = {}
    chip_def: dict[str, dict] = {}  # chip_slug -> {name, facet}
    chip_member_slugs: dict[str, set[str]] = {}  # chip_slug -> set of real slugs
    chip_member_names: dict[str, list[str]] = {}  # for searchability of "other" chips

    for tid, (slug, name, facet) in tag_meta.items():
        if facet is None:
            continue
        if slug not in freq:
            continue  # not used by any finalized comp
        n = freq[slug]
        if n >= OTHER_THRESHOLD:
            chip = slug
            chip_def[chip] = {"name": name, "facet": facet}
            chip_member_slugs.setdefault(chip, set()).add(slug)
            chip_member_names.setdefault(chip, []).append(name)
        else:
            chip = OTHER_SLUGS[facet]
            chip_def[chip] = {"name": "other", "facet": facet}
            chip_member_slugs.setdefault(chip, set()).add(slug)
            chip_member_names.setdefault(chip, []).append(name)
        slug_to_chip[slug] = chip

    # 5. Build the competition rows. Each comp's tagSlugs becomes the *chip*
    # slugs it maps to (deduped), so the UI selecting "domain-other" matches
    # any comp tagged with a long-tail domain tag.
    slug_to_name: dict[str, str] = {
        slug_: name_ for slug_, name_, _ in tag_meta.values()
    }

    competitions: list[dict] = []
    for row in comp_rows:
        cid = parse_int(row["Id"])
        raw_slugs = comp_tags.get(cid, set())
        chips: set[str] = set()
        for slug in raw_slugs:
            chip = slug_to_chip.get(slug)
            if chip:
                chips.add(chip)
        # tagText: all tag display names (including long-tail ones the UI
        # collapsed into "other") joined for substring search.
        tag_text = " ".join(sorted({slug_to_name.get(s, s) for s in raw_slugs}))
        competitions.append(
            {
                "id": cid,
                "slug": (row.get("Slug") or "").strip(),
                "title": (row.get("Title") or "").strip(),
                "subtitle": (row.get("Subtitle") or "").strip() or None,
                "hostSegment": (row.get("HostSegmentTitle") or "").strip() or None,
                "deadline": to_iso_date(row.get("DeadlineDate")),
                "metric": (row.get("EvaluationAlgorithmName") or "").strip() or None,
                "metricDescription": (
                    row.get("EvaluationAlgorithmDescription") or ""
                ).strip()
                or None,
                "rewardType": (row.get("RewardType") or "").strip() or None,
                "rewardQuantity": parse_float(row.get("RewardQuantity")),
                "tagSlugs": sorted(chips),
                "tagText": tag_text,
            }
        )

    competitions.sort(
        key=lambda c: (c["deadline"] is None, c["deadline"] or ""),
        reverse=True,
    )

    # 6. Tags list: chips ordered (data first, then task, then domain), within
    # each group: real chips by frequency desc, then the "other" chip last.
    facet_order = ["data", "task", "domain"]
    chips_by_facet: dict[str, list[tuple[str, dict]]] = {f: [] for f in facet_order}
    for chip, defn in chip_def.items():
        chips_by_facet[defn["facet"]].append((chip, defn))

    tags_out: list[dict] = []
    for facet in facet_order:
        items = chips_by_facet[facet]
        # Real (non-other) chips first by total uses across their members.
        real = [(c, d) for c, d in items if not c.endswith("-other")]
        other = [(c, d) for c, d in items if c.endswith("-other")]
        real.sort(key=lambda cd: -sum(freq[s] for s in chip_member_slugs[cd[0]]))
        for chip, defn in real:
            tags_out.append({"slug": chip, "name": defn["name"], "group": facet})
        for chip, defn in other:
            n_other_tags = len(chip_member_slugs[chip])
            tags_out.append(
                {
                    "slug": chip,
                    "name": "other",
                    "group": facet,
                    "otherCount": n_other_tags,
                }
            )

    bundle = {
        "generatedAt": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "tags": tags_out,
        "competitions": competitions,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))

    size_mb = out.stat().st_size / 1_048_576
    by_g = Counter(t["group"] for t in tags_out)
    print(
        f"wrote {len(competitions)} competitions, "
        f"chips: {dict(by_g)} ({size_mb:.2f} MB) -> {out}",
        file=sys.stderr,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv-dir", type=Path, default=Path("meta-kaggle"))
    ap.add_argument("--out", type=Path, default=Path("static/data/competitions.json"))
    args = ap.parse_args()
    build(args.csv_dir, args.out)


if __name__ == "__main__":
    main()
